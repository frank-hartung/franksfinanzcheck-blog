#!/usr/bin/env python3
"""blog_header_gate.py — Sicherheits-Header der ausgelieferten Seite prüfen (F-01).

Warum diese Wache existiert
--------------------------
Die Seite liegt auf GitHub Pages, und **GitHub Pages ignoriert
`static/_headers`**. Das steht als Kommentar in der Datei selbst — und ist der
Grund, warum live jahrelang HSTS, `X-Frame-Options` und `nosniff` fehlten:
Der Blog war in fremde Seiten einbettbar (Clickjacking auf „Jetzt anmelden“),
und der erste Aufruf über `http://` blieb ungeschützt.

Seit 15.10.2026 liegt die Zone hinter Cloudflare, und die Header kommen aus
einer **Transform Rule** (`cloudflare/edge-schutz.md`, Abschnitt A1). Diese
Wache prüft die Wirkung, nicht die Absicht: Sie holt die Startseite und eine
Unterseite und vergleicht die Kopfzeilen mit dem Soll.

Bauarten
--------
  --selftest   prüft die Prüfung (feste Fälle, kein Netz)  → in CI vor dem Lauf
  --offline    prüft nur die Konfigurationsdateien (Repo-Stand)
  (Vorgabe)    fragt die echte Seite ab (Netz nötig)

Ausgabe: Markdown-Bericht, Exit 1 bei fehlenden PFLICHT-Headern, Exit 0 sonst.
Optionale Header (Permissions-Policy, COOP/CORP) werden gemeldet, aber nicht
erzwungen — sie sind Härtung, kein Muss.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]

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


def kopfzeilen_holen(url: str, *, timeout: float = 20.0) -> tuple[int, dict[str, str]]:
    """HEAD-Anfrage; folgt Weiterleitungen und sammelt die letzten Kopfzeilen."""
    anfrage = urllib.request.Request(url, method="HEAD", headers={
        "user-agent": "franksfinanzcheck-header-wache/1.0 (+https://franksfinanzcheck.de/)",
        "accept": "text/html",
    })
    try:
        with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:
            return antwort.status, {k.lower(): v for k, v in antwort.headers.items()}
    except urllib.error.HTTPError as fehler:
        return fehler.code, {k.lower(): v for k, v in (fehler.headers or {}).items()}


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


def netz_pruefen() -> tuple[int, str]:
    zeilen = ["# Sicherheits-Header — Live-Prüfung", ""]
    fehlend_gesamt: list[str] = []
    warnungen_gesamt: list[str] = []
    for ziel in ZIELE:
        try:
            status, kopf = kopfzeilen_holen(ziel)
        except Exception as fehler:  # noqa: BLE001 – jede Netzstörung ist ein Befund
            fehlend_gesamt.append(f"`{ziel}` nicht erreichbar ({fehler}) — "
                                  "ohne Messung gilt der Stand als ungeprüft.")
            continue
        fehlend, warnungen, vorhanden = befunde_fuer(kopf)
        zeilen.append(f"## {ziel} (HTTP {status})")
        zeilen.append("")
        for z in vorhanden:
            zeilen.append(f"- ✅ `{z}`")
        for z in fehlend:
            zeilen.append(f"- ❌ {z}")
        for z in warnungen:
            zeilen.append(f"- ⚠️ {z}")
        zeilen.append("")
        fehlend_gesamt += [f"`{ziel}`: {f}" for f in fehlend]
        warnungen_gesamt += [f"`{ziel}`: {w}" for w in warnungen]
    zeilen.append("## Ergebnis")
    zeilen.append("")
    if fehlend_gesamt:
        zeilen.append(f"❌ {len(fehlend_gesamt)} Pflicht-Header fehlen oder sind falsch. "
                      "Die Regel aus `cloudflare/edge-schutz.md`, Abschnitt A1 ist "
                      "nicht aktiv oder unvollständig.")
        for f in fehlend_gesamt:
            zeilen.append(f"  - {f}")
        return 1, "\n".join(zeilen)
    zeilen.append("✅ Alle Pflicht-Header vorhanden und im Sollbereich.")
    if warnungen_gesamt:
        zeilen.append(f"⚠️ {len(warnungen_gesamt)} Hinweise (Härtung, kein Fehler).")
    return 0, "\n".join(zeilen)


# ------------------------------------------------------------------ Selbsttest
def selftest() -> int:
    gut = {
        "strict-transport-security": "max-age=31536000; includeSubDomains; preload",
        "x-content-type-options": "nosniff",
        "x-frame-options": "DENY",
        "referrer-policy": "strict-origin-when-cross-origin",
        "content-security-policy": ("default-src 'self'; object-src 'none'; base-uri 'self'; "
                                    "frame-ancestors 'none'; "
                                    "frame-src https://challenges.cloudflare.com; "
                                    "form-action 'self' https://abos.franksfinanzcheck.de"),
    }
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

    print(f"✅ SELBSTTEST OK — {faelle} Fälle grün (Pflicht-Header, CSP-Anweisungen, "
          "Clickjacking, HSTS-Frist, Repo-Stand).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prüft die Sicherheits-Header der Seite (F-01).")
    parser.add_argument("--selftest", action="store_true", help="prüft die Prüfung (ohne Netz)")
    parser.add_argument("--offline", action="store_true", help="nur Repo-Stand prüfen")
    parser.add_argument("--json", action="store_true", help="Befunde als JSON")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    code, bericht = (offline_pruefen() if args.offline else netz_pruefen())
    if args.json:
        print(json.dumps({"exit": code, "bericht": bericht}, ensure_ascii=False, indent=2))
    else:
        print(bericht)
    return code


if __name__ == "__main__":
    sys.exit(main())
