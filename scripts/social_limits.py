#!/usr/bin/env python3
# ============================================================
#  SOCIAL-GRENZEN – eine Quelle für Kartentexte und Bildmaße
#  (Neuaufbau 28.10.2026, SEO-Parität „Social-Vorschau“)
#
#  WARUM ES DIESE DATEI GIBT
#  -------------------------
#  Die Vorschau-Werkstatt (tools/social-vorschau/) zeigt, wie ein
#  Artikel bei X, Facebook, LinkedIn, WhatsApp, Slack und Pinterest
#  aussieht. Diese Ansicht ist nur dann mehr als Dekoration, wenn die
#  Abschneidegrenzen NICHT im JavaScript stehen: Eine Zahl im Frontend
#  ist eine Zahl, die niemand prüft – und die still veraltet.
#
#  Deshalb gilt hier dieselbe Regel wie bei serp_limits.py: Grenzen
#  stehen an EINER Stelle, der Generator liest sie als Import, und die
#  Oberfläche bekommt sie als Datensatz mitgeliefert. Ändert jemand
#  eine Grenze, ändern sich Bericht, CSV und Vorschau gemeinsam.
#
#  WAS DARAN EHRLICH IST (und was nicht)
#  -------------------------------------
#  Google dokumentiert Snippet-Grenzen (siehe serp_limits.py). Kein
#  soziales Netzwerk dokumentiert verbindlich, ab welchem Zeichen es
#  Titel oder Beschreibung kürzt – die Kürzung hängt an Client,
#  Viewport, Schrift und Sprachraum. Die Zahlen unten sind deshalb
#  bewusst als **Richtwerte** deklariert: gemessene Konventionen,
#  Stand 10/2026, mit Quelle. Ein Befund hier heißt „prüfen“, nicht
#  „falsch“. Die Vorschau zeigt zusätzlich die volle Länge an, damit
#  niemand eine Kürzung für einen Textfehler hält.
#
#  Die Grenzen sind absichtlich konservativ: Lieber ein Hinweis zu
#  viel als eine Karte, deren Nutzenversprechen im Client abgeschnitten
#  wird. Genau das ist der Punkt, an dem Leser NICHT klicken.
# ============================================================
"""Kanalgrenzen und Bildmaße für die Social-Vorschau (SSOT, ohne Abhängigkeiten)."""

from __future__ import annotations

STAND = "2026-10"

# Empfohlene Bildmaße für Link-Karten (OpenGraph). Untergrenze ist das,
# was X/Facebook/LinkedIn für die große Karte noch akzeptieren; darunter
# zeigt der Client ein kleines Vorschaubild oder gar keins.
BILD_MIN_BREITE = 600
BILD_MIN_HOEHE = 315
BILD_IDEAL_BREITE = 1200
BILD_IDEAL_HOEHE = 630
BILD_MAX_BYTES = 8 * 1024 * 1024

# Zielseitenverhältnis der großen Karte (1.91:1) und die Toleranz, ab der
# ein Beschnitt sichtbar wird. 10 % ist die Grenze, ab der ein 1200×630-
# Layout merklich anders beschnitten wird als beabsichtigt.
VERHAELTNIS_ZIEL = BILD_IDEAL_BREITE / BILD_IDEAL_HOEHE
VERHAELTNIS_TOLERANZ = 0.10

# Kanäle in Anzeigereihenfolge. `titel_max` / `beschreibung_max` in Zeichen,
# `quelle` nennt die Herkunft des Richtwerts, `notiz` erklärt die Kürzung.
KANAELE: tuple[dict, ...] = (
    {
        "id": "x",
        "name": "X (Twitter)",
        "karte": "summary_large_image",
        "titel_max": 70,
        "beschreibung_max": 200,
        "verhaeltnis": "gross",
        "notiz": "Große Karte: Titel zwei Zeilen, Beschreibung zwei Zeilen. "
                 "Die harte Grenze hängt am Client (Web, iOS, Android).",
        "quelle": "X Developer Platform, Cards Markup (summary_large_image)",
    },
    {
        "id": "facebook",
        "name": "Facebook",
        "karte": "Link-Vorschau",
        "titel_max": 65,
        "beschreibung_max": 155,
        "verhaeltnis": "gross",
        "notiz": "Meta kürzt Titel und Beschreibung je nach Fläche unterschiedlich; "
                 "im Feed sind rund zwei Titelzeilen sichtbar.",
        "quelle": "Meta Sharing Debugger, beobachtete Feed-Darstellung",
    },
    {
        "id": "linkedin",
        "name": "LinkedIn",
        "karte": "Link-Vorschau",
        "titel_max": 70,
        "beschreibung_max": 140,
        "verhaeltnis": "gross",
        "notiz": "LinkedIn zeigt Titel und Beschreibung mehrzeilig, schneidet "
                 "die Beschreibung im Feed jedoch früh ab.",
        "quelle": "LinkedIn Post Inspector, beobachtete Feed-Darstellung",
    },
    {
        "id": "whatsapp",
        "name": "WhatsApp",
        "karte": "Link-Karte",
        "titel_max": 65,
        "beschreibung_max": 130,
        "verhaeltnis": "gross",
        "notiz": "Mobil zwei Titelzeilen und drei Beschreibungszeilen; "
                 "WhatsApp lädt das Vorschaubild selbst nach.",
        "quelle": "WhatsApp-Link-Vorschau, beobachtete Darstellung",
    },
    {
        "id": "slack",
        "name": "Slack",
        "karte": "Unfurl",
        "titel_max": 100,
        "beschreibung_max": 300,
        "verhaeltnis": "gross",
        "notiz": "Slack zeigt mehr Text als die sozialen Netze, oft mit "
                 "zusätzlichem Seitentitel als Quelle.",
        "quelle": "Slack-Unfurl, beobachtete Darstellung",
    },
    {
        "id": "pinterest",
        "name": "Pinterest",
        "karte": "Rich Pin",
        "titel_max": 100,
        "beschreibung_max": 500,
        "verhaeltnis": "hoch",
        "notiz": "Pinterest ist ein Hochformat-Kanal (2:3). Ein 1.91:1-Cover "
                 "wird im Pin beschnitten – das ist kein Fehler, aber eine Entscheidung.",
        "quelle": "Pinterest Rich Pins, Bildempfehlungen 2:3",
    },
)

# Pinterest-Zielformat (Hochformat) für den Hinweis in der Vorschau.
PIN_ZIEL = (1000, 1500)


def kanaele() -> list[dict]:
    """Kopfdaten für UI, CSV und Tests – eine flache, JSON-fähige Liste."""
    return [dict(k) for k in KANAELE]


def kanal(kanal_id: str) -> dict | None:
    return next((dict(k) for k in KANAELE if k["id"] == kanal_id), None)


def _kuerzt(text: str, grenze: int) -> bool:
    return len(text) > grenze


def text_befunde(titel: str, beschreibung: str) -> list[dict]:
    """Befunde zu Titel/Beschreibung je Kanal.

    Jeder Befund trägt `kanal`, `code`, `schwere`, `detail`, `massnahme`.
    Die Schwere ist bewusst zurückhaltend: Ein zu langer Titel ist kein
    technischer Fehler (P1), sondern eine redaktionelle Entscheidung (P3);
    eine fehlende Beschreibung dagegen verschenkt die ganze Karte (P2).
    """
    befunde: list[dict] = []
    titel, beschreibung = (titel or "").strip(), (beschreibung or "").strip()
    for k in KANAELE:
        if not titel:
            befunde.append({
                "kanal": k["id"], "code": "social-titel", "schwere": "P2",
                "detail": "Kein og:title – die Karte zeigt nur die Domain.",
                "massnahme": "Titel im Frontmatter setzen; er wird als og:title ausgegeben.",
            })
        elif _kuerzt(titel, k["titel_max"]):
            befunde.append({
                "kanal": k["id"], "code": "social-titel", "schwere": "P3",
                "detail": f"Titel {len(titel)} Zeichen, Richtwert {k['titel_max']}.",
                "massnahme": "Nutzenversprechen in die ersten Wörter ziehen; der Rest wird abgeschnitten.",
            })
        if not beschreibung:
            befunde.append({
                "kanal": k["id"], "code": "social-beschreibung", "schwere": "P2",
                "detail": "Keine og:description – die Karte bleibt ohne Nutzenzeile.",
                "massnahme": "Description im Frontmatter setzen.",
            })
        elif _kuerzt(beschreibung, k["beschreibung_max"]):
            befunde.append({
                "kanal": k["id"], "code": "social-beschreibung", "schwere": "P3",
                "detail": f"Beschreibung {len(beschreibung)} Zeichen, Richtwert {k['beschreibung_max']}.",
                "massnahme": "Kernsatz nach vorn; was danach steht, zeigt der Client nicht.",
            })
    return befunde


def bild_befunde(breite: int | None, hoehe: int | None, groesse: int | None = None) -> list[dict]:
    """Befunde zu og:image – kanalunabhängig, weil alle Kanäle dasselbe Bild lesen.

    `breite`/`hoehe` kommen aus dem Dateikopf (social_vorschau.bild_masse).
    `None` heißt „kein Bild“ – dann ist das der P1-Befund, nicht eine
    Schätzung. Unbekannte Maße werden NICHT geraten.
    """
    befunde: list[dict] = []
    if not breite or not hoehe:
        return [{
            "kanal": "*", "code": "social-bild", "schwere": "P1",
            "detail": "Kein og:image – die Karte erscheint ohne Bild.",
            "massnahme": "cover.image im Frontmatter setzen (1200×630 oder 1000×1500).",
        }]
    if groesse and groesse > BILD_MAX_BYTES:
        befunde.append({
            "kanal": "*", "code": "social-bild-groesse", "schwere": "P2",
            "detail": f"{groesse / 1024 / 1024:.1f} MB – über {BILD_MAX_BYTES // 1024 // 1024} MB.",
            "massnahme": "Bild komprimieren; große Dateien werden von Clients übersprungen.",
        })
    if breite < BILD_MIN_BREITE or hoehe < BILD_MIN_HOEHE:
        befunde.append({
            "kanal": "*", "code": "social-bild-klein", "schwere": "P2",
            "detail": f"{breite}×{hoehe} px – unter {BILD_MIN_BREITE}×{BILD_MIN_HOEHE} px.",
            "massnahme": f"Auf mindestens {BILD_IDEAL_BREITE}×{BILD_IDEAL_HOEHE} px liefern.",
        })
    verhaeltnis = breite / hoehe
    if abs(verhaeltnis - VERHAELTNIS_ZIEL) / VERHAELTNIS_ZIEL > VERHAELTNIS_TOLERANZ:
        # EIN Befund, nicht zwei: Ein Hochformat-Cover (typisch 2:3) ist für
        # Pinterest richtig und für Feed-Karten beschnitten. Zwei getrennte
        # Befunde („falsches Format" + „Pin-Format") hätten denselben Sach-
        # verhalt doppelt gemeldet – 152 Zeilen für 76 Seiten, aus denen
        # niemand eine Entscheidung ableiten kann.
        if verhaeltnis < 1.0:
            detail = (f"Hochformat {breite}×{hoehe} px (Ziel Pinterest "
                      f"{PIN_ZIEL[0]}×{PIN_ZIEL[1]}); in Feed-Karten (1.91:1) wird beschnitten.")
            massnahme = ("Bewusst entscheiden: Hochformat für Pinterest behalten oder ein "
                         "1.91:1-Zweitbild für X/Facebook/LinkedIn liefern.")
        else:
            detail = f"Seitenverhältnis {verhaeltnis:.2f}:1 statt 1.91:1."
            massnahme = "Für Feed-Karten 1.91:1 zuschneiden; Hochformat ist nur bei Pinterest richtig."
        befund = {"kanal": "*", "code": "social-bild-format", "schwere": "P3",
                  "detail": detail, "massnahme": massnahme}
        if verhaeltnis < 1.0:
            # Auf Pinterest ist Hochformat RICHTIG. Der Befund gilt dort
            # nicht – sonst widerspräche die Vorschau dem eigenen Kanal-
            # Hinweis („2:3 empfohlen") auf derselben Karte.
            befund["ausser"] = ["pinterest"]
        befunde.append(befund)
    return befunde


def zusammenfassung(pages: list[dict]) -> dict:
    """Zählwerk für den Kopf der Vorschau – aus denselben Befunden, nicht daneben."""
    codes: dict[str, int] = {}
    schwere: dict[str, int] = {}
    for page in pages:
        for b in page.get("befunde", []):
            codes[b["code"]] = codes.get(b["code"], 0) + 1
            schwere[b["schwere"]] = schwere.get(b["schwere"], 0) + 1
    return {
        "seiten": len(pages),
        "ohne_bild": sum(1 for p in pages if not p.get("bild_breite")),
        "befunde": sum(codes.values()),
        "codes": dict(sorted(codes.items())),
        "schwere": dict(sorted(schwere.items())),
        "stand": STAND,
    }


def selftest() -> int:
    """Beweist die Grenzen an Beispielen, bevor die Vorschau sie zeigt."""
    fails: list[str] = []
    if kanal("x") is None or kanal("gibtsnicht") is not None:
        fails.append("kanal()-Lookup liefert falsche Treffer")
    ids = [k["id"] for k in KANAELE]
    if len(ids) != len(set(ids)):
        fails.append("doppelte Kanal-IDs")
    for k in KANAELE:
        if k["titel_max"] <= 0 or k["beschreibung_max"] <= 0:
            fails.append(f"{k['id']}: unbrauchbare Grenze")
        if not k["quelle"]:
            fails.append(f"{k['id']}: Quelle fehlt (Richtwert ohne Herkunft)")
        if k["titel_max"] > k["beschreibung_max"]:
            fails.append(f"{k['id']}: Titel-Grenze größer als Beschreibungs-Grenze")
    # Ein Titel unter allen Grenzen erzeugt keinen Befund.
    kurz = text_befunde("Strom sparen", "Stromfresser finden und Tarife vergleichen.")
    if kurz:
        fails.append(f"kurzer, sauberer Text erzeugt Befunde: {kurz}")
    # Ein langer Titel erzeugt genau für die Kanäle einen Befund, deren
    # Richtwert überschritten ist – nicht pauschal für alle.
    lang = text_befunde("T" * 80, "B" * 200)
    titel_befunde = [b for b in lang if b["code"] == "social-titel"]
    erwartet = sum(1 for k in KANAELE if k["titel_max"] < 80)
    if len(titel_befunde) != erwartet:
        fails.append(f"langer Titel: {len(titel_befunde)} statt {erwartet} Befunde")
    if not titel_befunde or {b["kanal"] for b in titel_befunde} >= set(ids):
        fails.append("Titelbefunde decken Kanäle mit hoher Grenze mit ab")
    # Fehlendes Bild ist P1 und keine Schätzung.
    if bild_befunde(None, None)[0]["code"] != "social-bild":
        fails.append("fehlendes Bild nicht als social-bild gemeldet")
    if bild_befunde(None, None)[0]["schwere"] != "P1":
        fails.append("fehlendes Bild nicht als P1 gemeldet")
    # Passendes Bild (1200×630) erzeugt keinen Befund.
    if bild_befunde(1200, 630, groesse=400_000):
        fails.append(f"ideales Bild erzeugt Befunde: {bild_befunde(1200, 630, 400_000)}")
    # Zu kleines, falsches und zu großes Bild werden unterschieden.
    codes = {b["code"] for b in bild_befunde(400, 400, groesse=20 * 1024 * 1024)}
    if codes != {"social-bild-klein", "social-bild-format", "social-bild-groesse"}:
        fails.append(f"Bildbefunde unvollständig: {sorted(codes)}")
    # Hochformat ergibt GENAU EINEN Befund (kanalunabhängig) – nicht zwei
    # Meldungen für denselben Sachverhalt.
    hoch = bild_befunde(1000, 1500)
    if len(hoch) != 1 or hoch[0]["code"] != "social-bild-format":
        fails.append(f"Hochformat ergibt {len(hoch)} statt 1 Befund: {hoch}")
    if hoch and "Pinterest" not in hoch[0]["detail"]:
        fails.append("Hochformat-Befund nennt Pinterest nicht")
    if hoch and "pinterest" not in hoch[0].get("ausser", []):
        fails.append("Hochformat-Befund gilt fälschlich auch für Pinterest")
    # Zusammenfassung zählt aus den Befunden.
    summ = zusammenfassung([
        {"bild_breite": 1200, "befunde": [{"code": "social-titel", "schwere": "P3"}]},
        {"bild_breite": None, "befunde": [{"code": "social-bild", "schwere": "P1"}]},
    ])
    if summ["seiten"] != 2 or summ["ohne_bild"] != 1 or summ["befunde"] != 2:
        fails.append(f"Zusammenfassung falsch: {summ}")
    if fails:
        for f in fails:
            print(f"❌ Social-Grenzen: {f}")
        return 2
    print(f"✅ Social-Grenzen: {len(KANAELE)} Kanäle, Bildmaße und Grenzen "
          f"belegt (Stand {STAND}) – Vorschau und Bericht lesen dieselbe Quelle.")
    return 0


def main() -> int:
    import sys
    if "--selftest" in sys.argv:
        return selftest()
    import json
    print(json.dumps({"stand": STAND, "kanaele": kanaele()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
