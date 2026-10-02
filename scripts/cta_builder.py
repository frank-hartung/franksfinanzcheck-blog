#!/usr/bin/env python3
# ============================================================
#  CTA-BUILDER – WERKSTATT FÜR DEN END-CTA (eine Wahrheit für
#  alle Autoren der Content-Pipeline)
#
#  REPARATUR 02.10.2026 (Vorgang WF-D4E0, Issue #513 –
#  Content-Reserve-Workflow dauerhaft grün):
#
#  DREI unabhängige Autoren (ki_shared.cta_block,
#  engine_generate.save_article, generate_drafts.write_draft)
#  schrieben bis heute jeweils ihre eigene End-CTA-Kopie –
#  alle drei mit demselben Defekt:
#      👉 **Jetzt vergleichen und sparen:**
#      [**→ Jetzt Angebote vergleichen**](https://a.check24.net/…)
#    1. ROHE PARTNER-URL statt /go/-Übergabeseite. Die Link-
#       Integritätswache (affiliate_link_check/affiliate_integrity_gate)
#       verwirft jeden Artikel mit roher Partner-URL im Text.
#    2. IW8 – ANKER NENNT KEIN ANGEBOT. „Jetzt Angebote vergleichen“
#       sagt dem Leser nicht, wohin der Klick führt.
#    3. IW3 – „VERGLEICH“ VOR EINZELANGEBOT. Themen mit CTA zu einer
#       C24-Bank-Route versprachen einen Marktvergleich, den es dort
#       nicht gibt.
#  Folge: JEDER maschinell erzeugte Reserve-Kandidat scheiterte bei
#  der Reserve-Zertifizierung am Affiliate-Gate – die Reserve leerte
#  sich nachts strukturell, obwohl Autoren und Heiler „grün“ meldeten.
#
#  LÖSUNG: Satz UND Anker kommen ausschließlich aus
#  affiliate_intent_contract.cta_bausteine() – derselben Wahrheit,
#  gegen die die Intent-Wache (IW0–IW9) den Bestand prüft – und das
#  Ziel ist IMMER die /go/-Übergabeseite, die der Kontrakt zur Route
#  kennt. Dieses Modul hat bewusst KEINE Imports aus anderen
#  Repo-Skripten (nur stdlib + yaml + contract), damit Autoren ohne
#  Import-Zyklus-Gefahr darauf zugreifen können.
# ============================================================
"""End-CTA nach Kontrakt: Satz, Anker und /go/-Ziel aus einer Quelle."""

from __future__ import annotations

import os
import re

import yaml

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

END_DISCLOSURE = (
    "Dieser Artikel enthält Affiliate-Links (Werbung). Beim Abschluss "
    "über einen Link erhalten wir eine Provision – für dich entstehen "
    "keine Mehrkosten."
)

_END_SATZ_FALLBACK = "Jetzt vergleichen und sparen:"


def route_fuer_url(url: str) -> str:
    """Partner-URL → /go/-Routenschlüssel (Quelle: check24_links.yaml).

    Deterministisch aus derselben YAML, aus der die Übergabeseiten
    gebaut werden. Unbekannte URLs landen ehrlich beim Portal-
    Schlüssel „allgemein“ – niemals still bei einem andersartigen
    Einzelangebot. Bereits korrekte /go/-Pfade passieren unverändert.
    """
    u = (url or "").strip()
    if not u:
        return ""
    m = re.match(r"^/go/([a-z0-9-]+)/?$", u)
    if m:
        return m.group(1)
    try:
        with open(os.path.join(BLOG_DIR, "scripts", "check24_links.yaml"),
                  encoding="utf-8") as fh:
            links = (yaml.safe_load(fh) or {}).get("links", {}) or {}
        for key, ref in links.items():
            if str(ref).strip() == u:
                return str(key)
    except Exception:                                   # noqa: BLE001
        pass
    if "check24.net" in u or "partner-versicherung.de" in u:
        return "allgemein"
    return ""


def cta_end_block(affiliate_url: str | None = None, route: str = "",
                  slug: str = "") -> str:
    """Kompletter End-CTA (Marker, Kontrakt-Satz/-Anker, /go/-Ziel,
    Werbe-Offenlegung) – bytegleich zum von der Intent-Wache
    freigegebenen Hausmuster.

    - `route` hat Vorrang; fehlt sie, wird sie aus `affiliate_url`
      abgeleitet; beides leer → Portal-Route „allgemein“.
    - `slug` stabilisiert die Anker-Variante pro Artikel (kein
      täglicher Text-Churn, Idempotenz der Wache).
    """
    key = (route or "").strip() or route_fuer_url(affiliate_url or "")
    satz, anker = "", ""
    try:
        import affiliate_intent_contract as aic
        key = key or "allgemein"
        satz, anker = aic.cta_bausteine(key, "end", slug)
    except Exception as exc:                            # noqa: BLE001
        print(f"  ⚠ Kontrakt-CTA nicht verfügbar ({exc}) – Portal-Fallback")
        key = key or "allgemein"
    satz = (satz or "").strip()
    if not satz:
        satz = _END_SATZ_FALLBACK
    elif not satz.endswith(":"):
        satz += ":"
    if not anker:
        anker = "→ Jetzt Angebote ansehen"
    url = f"/go/{key}/"
    return (
        "\n---\n\n"
        f"👉 **{satz}** [**{anker}**]({url})\n\n"
        f"*{END_DISCLOSURE}*\n"
    )


def _selftest() -> list[str]:
    """Fail-closed: der End-CTA muss gegen die Kontrakt-Wahrheit bestehen."""
    fehler: list[str] = []
    block = cta_end_block(route="allgemein", slug="probe-artikel")
    if "http" in block:
        fehler.append("End-CTA enthält rohe URL statt /go/-Redirect")
    if "/go/allgemein/" not in block:
        fehler.append("Portal-Route fehlt im Default-End-CTA")
    if "CHECK24" not in block:
        fehler.append("Default-Anker nennt die Marke nicht (IW8)")
    if "*Werbung*" not in block and "Werbung" not in block:
        fehler.append("Werbe-Offenlegung fehlt im End-CTA")
    c24 = cta_end_block(route="tagesgeld", slug="probe-artikel")
    if "/go/tagesgeld/" not in c24 or "C24" not in c24:
        fehler.append("C24-Route ohne Routenziel oder Markennennung")
    low = re.findall(r"vergleich\w*", c24.lower())
    if low:
        fehler.append(f"C24-CTA verspricht Vergleich (IW3): {low}")
    a = cta_end_block(route="gas", slug="probe-artikel")
    b = cta_end_block(route="gas", slug="probe-artikel")
    if a != b:
        fehler.append("End-CTA nicht deterministisch (Slug-Stabilisator)")
    if route_fuer_url("/go/strom/") != "strom":
        fehler.append("/go/-Pfad wird nicht als Route erkannt")
    try:
        with open(os.path.join(BLOG_DIR, "scripts", "check24_links.yaml"),
                  encoding="utf-8") as fh:
            links = (yaml.safe_load(fh) or {}).get("links", {}) or {}
        url = str(links.get("tagesgeld", ""))
        if url and route_fuer_url(url) != "tagesgeld":
            fehler.append("URL→Route-Abbildung (tagesgeld) fehlerhaft")
    except Exception as exc:                            # noqa: BLE001
        fehler.append(f"check24_links.yaml nicht lesbar: {exc}")
    return fehler


if __name__ == "__main__":
    errs = _selftest()
    if errs:
        print("❌ cta_builder-Selbsttest:")
        for e in errs:
            print(f"   - {e}")
        raise SystemExit(1)
    print("✅ cta_builder-Selbsttest: End-CTA konform zum Intent-Kontrakt.")
