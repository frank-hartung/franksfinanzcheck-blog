#!/usr/bin/env python3
"""newsletter_qa.py – die Vor-Versand-Wache des Newsletters (Pre-Send-Validator).

WARUM
-----
Ein Newsletter, der einmal falsch hinausgeht, kostet mehr als ein Monat Arbeit:
Abmeldungen, ein angeschossener Sender-Ruf – und bei fehlendem Abmeldelink oder
erfundener Sparsumme auch Post von der Verbraucherschutzstelle. Kommerzielle
Plattformen verkaufen genau hier eine Prüfung vor dem Versand (Rendering, Links,
Ton, Kompatibilität). Diese Wache ist dasselbe Versprechen – als Code im Repo,
0 Euro, ohne Netz:

  * Sie prüft das Gebaute (HTML + Text + Betreff + Preheader), nicht die Absicht.
  * Jeder Fund trägt eine Regelkennung (Q1…Q21) und den Grund der Regel.
  * Sie misst, was messbar ist (Kontrast, Größe, Linkzahl, Wortzahl) statt zu
    schätzen – derselbe Maßstab wie `e2e/design-metrics.mjs`.

EINBAU: `scripts/newsletter_digest.py` lässt jede Ausgabe durch diese Wache,
bevor versendet wird. Funde blockieren den Live-Versand; Bauen bleibt möglich –
ein Tippfehler im Betreff darf nicht die Produktion stoppen, nur den Versand.

Nutzung:
    python3 scripts/newsletter_qa.py --build --days 1 [--json|--md]
    python3 scripts/newsletter_qa.py --datei .cache/nl/ausgabe.html \
        --text .cache/nl/ausgabe.txt --betreff "5 Sparechnungen für 22.09.2026"
    python3 scripts/newsletter_qa.py --selftest

Exit: 0 = bestanden · 1 = Fund · 2 = Fehler (Prüfung ausgefallen)
"""
from __future__ import annotations

import argparse
import datetime
import glob
import html as _html
import json
import os
import re
import sys
import urllib.parse

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newsletter_studio as studio                       # noqa: E402
import newsletter_schedule as plan                        # noqa: E402

GMAIL_CLIP_BYTES = 102_400        # darüber clippt Gmail – und schneidet Footer + Abmeldung ab
FRUEH_BYTES = 90_000
MIN_TXT_BYTES = 240
ERLAUBTE_HOSTS = ("franksfinanzcheck.de", "brevo.com", "sendinblue.com")
EIGENE_ABSENDER_DOMAIN = ("franksfinanzcheck.de",)
MOJIBAKE = ("Ã¼", "Ã¶", "Ã¤", "ÃŸ", "â€™", "â€œ", "â€“", "Ã¢â‚¬", "Âµ")
GROSS_WEISS = {"DSL", "WLAN", "TV", "LED", "USB", "HD", "5G", "EU", "BGH", "ADAC", "GmbH",
               "AG", "NH", "ZBFS", "UWG", "DSGVO", "AVV"}
PREHEADER_KLISCHEE = ("if you can't see", "wenn sie diese mail nicht sehen",
                      "kannst du diese mail nicht sehen", "view in browser")
VERBOTENES_LAYOUT = ("display:flex", "display: grid", "display:grid", "position:absolute",
                     "position:fixed", "column-count")

REGELN = {
    "Q1": "Größe: über 102 KB clippt Gmail – Abmeldelink und Impressum fallen weg",
    "Q2": "Struktur: Tabellen-Layout, kein Flex/Grid, kein Script/Form/@import/Iframe",
    "Q3": "Vorlagen-Syntax: nur die Marken des Anbieters, keine Einzelklammer, kein Leak",
    "Q4": "Links: absolute https-Links auf erlaubte Hosts, mit Text, kein Anker ins Leere",
    "Q5": "Bilder: alt + Breite + Höhe, keine fremden Hosts, kein background-image",
    "Q6": "Textmenge: eine Mail aus Bildern ist Spam, eine ohne Substanz Abmeldegrund",
    "Q7": "Ton: Angstmache-, Hype- und Großbuchstaben-Signale (UWG nah, Spamfilter nah)",
    "Q8": "Betreff: Länge, Markenzeile, kein Antwortzusatz, kein Markup",
    "Q9": "Preheader: eigener Satz in der Inbox-Vorschau, keine Betreff-Kopie, kein Klischee",
    "Q10": "Rechtliches in der Fußzeile: Anschrift, Impressum, Datenschutz, DOI, Werbung",
    "Q11": "Kontrast gemessen (WCAG 2.1) statt geschätzt – in hell und dunkel",
    "Q12": "Textalternative gleichwertig: jeder Link, jede Zahl, jede Rechtszeile",
    "Q13": "Mobil und tippbar: Schriftgröße, Button-Höhe, feste Containerbreite",
    "Q14": "Dokumentkopf: Doctype, lang, Charset, Viewport, color-scheme, Titel",
    "Q15": "Betreff-Wiederholung: dieselbe Zeile zweimal ist der schnellste Abmeldegrund",
    "Q16": "Zahlen-Belegpflicht: keine Ersparnis in Betreff, Preheader oder Hero ohne Quelle",
    "Q17": "Block-Vollständigkeit: Titel, Text, /posts/-Ziel, keine Duplikate, max_artikel",
    "Q18": "Zeichensatz: kein Mojibake, keine doppelten Entities, keine unbekannte Entity",
    "Q19": "Datenschutz im Versand: kein Tracking, ein Klick zur Abmeldung",
    "Q20": "Absender: Name und Antwortadresse gehören zur eigenen, authentifizierten Domain",
    "Q21": "Kadenz: Dienstag/Freitag – kein Werktags-Versprechen, Versandtag im Kopf, "
           "nächste Ausgabe auf einem echten Versandtag",
}


def _regel(code: str, msg: str, schwere: str = "fund") -> dict:
    return {"regel": code, "titel": REGELN.get(code, ""), "meldung": msg, "schwere": schwere}


def _sichtbarer_text(html: str) -> str:
    ohne = re.sub(r"<(style|head)[^>]*>.*?</\1>", " ", html, flags=re.S)
    ohne = re.sub(r"<!--.*?-->", " ", ohne, flags=re.S)
    ohne = re.sub(r"<[^>]+>", " ", ohne)
    return studio._clean(_html.unescape(ohne))


# ------------------------------------------------------------------- Prüfkern
def pruefe(email: dict, *, konf: dict, materiale: list[dict] | None = None,
           zustand: dict | None = None, root: str = BLOG_DIR) -> dict:
    """Ein gebautes E-Mail gegen 21 Regeln.

    → {"bestanden", "score", "funde", "warnungen", "messwerte", "regeln_geprueft"}
    """
    funde: list[dict] = []
    warnungen: list[dict] = []
    html = email.get("html", "") or ""
    text = email.get("text", "") or ""
    betreff = (email.get("betreff") or "").strip()
    pre = (email.get("preheader") or "").strip()
    e_mail = konf.get("email", {})
    creative = konf.get("creative", {})
    blöcke = email.get("blocks", []) or []
    rein = _sichtbarer_text(html)
    worter = [w for w in re.split(r"\s+", rein) if w]

    # ---- Q1 Größe ---------------------------------------------------------
    groesse = len(html.encode("utf-8"))
    if groesse > GMAIL_CLIP_BYTES:
        funde.append(_regel("Q1", f"HTML ist {groesse:,} Bytes – über {GMAIL_CLIP_BYTES:,} "
                                  "clippt Gmail und schneidet Abmeldelink wie Impressum ab"))
    elif groesse > FRUEH_BYTES:
        warnungen.append(_regel("Q1", f"HTML ist {groesse:,} Bytes – Frühwarnung vor der "
                                      f"{GMAIL_CLIP_BYTES:,}-Byte-Grenze", "warnung"))
    if len(text.encode("utf-8")) < MIN_TXT_BYTES:
        funde.append(_regel("Q1", f"Textfassung hat nur {len(text)} Zeichen – die Mail ist "
                                  "nicht ohne HTML lesbar"))

    # ---- Q2 Struktur ------------------------------------------------------
    if 'role="presentation"' not in html and "role=presentation" not in html:
        funde.append(_regel("Q2", "kein Tabellen-Layout (role=\"presentation\") – Outlook zerlegt "
                                  "ein Div-Gerüst in Einzelstücke"))
    for tag, grund in (("<script", "Skripte laufen in Mails nicht und heben die Spamnote"),
                       ("<form", "Formulare in Mails sind toter Code – die Anmeldung gehört auf die Site"),
                       ("@import", "fremde CSS-Datei: Outlook ignoriert sie, Gmail clippt die Mail"),
                       ("<iframe", "Iframes blocken die meisten Clients")):
        if tag.lower() in html.lower():
            funde.append(_regel("Q2", f"{tag} im E-Mail – {grund}"))
    for eig in VERBOTENES_LAYOUT:
        if eig in html:
            funde.append(_regel("Q2", f"{eig} im E-Mail – Outlook und Gmail-Web bauen das um "
                                      "oder streichen es; Layout läuft über Tabellen"))

    # ---- Q3 Vorlagen-Syntax ----------------------------------------------
    marken = e_mail.get("marken") or {}
    for name, wert in marken.items():
        if not wert:
            continue
        if wert not in html:
            funde.append(_regel("Q3", f"Platzhalter {wert} für {name} fehlt im HTML – ohne ihn "
                                      "linkt die Mail ins Leere"))
    alt = re.findall(r"(?<!\{)\{(unsubscribe|mirror|update_profile|doubleoptin)\}(?!\})", html + text)
    if alt:
        funde.append(_regel("Q3", f"Einzelklammer-Marke(n) {sorted(set(alt))} – die Neue Template "
                                  "Language erwartet doppelte Klammern; sonst steht „{unsubscribe}“ "
                                  "als Wort im Mail und der Abmeldelink ist kaputt"))
    erlaubt = set(marken.values()) | {"{{unsubscribe}}", "{{mirror}}", "{{update_profile}}",
                                       "{{doubleoptin}}"}
    for leak in set(re.findall(r"\{\{[^{}]{1,40}\}\}", html)):
        if leak.strip() not in erlaubt:
            funde.append(_regel("Q3", f"unbekannter Platzhalter {leak} – der Anbieter ersetzt ihn "
                                      "nicht, er wird als Code ausgeliefert"))

    # ---- Q4 Links ---------------------------------------------------------
    hrefs = re.findall(r'<a[^>]+href="([^"]*)"', html)
    fremde = []
    https_ziele = 0
    for href in hrefs:
        if href.startswith("{{"):
            continue
        if href.startswith("mailto:"):
            if not re.fullmatch(r"mailto:[^@\s]+@[^@\s]+\.[A-Za-z]{2,}", href):
                funde.append(_regel("Q4", f"Antwortadresse {href!r} ist keine gültige Mail-Adresse"))
            continue
        if not href.strip() or href == "#":
            funde.append(_regel("Q4", "leeres Linkziel (#) im E-Mail – der Klick passiert nichts"))
            continue
        u = urllib.parse.urlsplit(href)
        if u.scheme != "https":
            funde.append(_regel("Q4", f"Link {href!r} ist {u.scheme or 'relativ'} – relative Links "
                                      "funktionieren im Postfach nicht, unverschlüsselte gehören "
                                      "nicht in eine Mail mit Personenbezug"))
            continue
        https_ziele += 1
        host = (u.hostname or "").lower()
        if not any(host == h or host.endswith("." + h) for h in ERLAUBTE_HOSTS):
            fremde.append(host)
    for host in sorted(set(fremde)):
        warnungen.append(_regel("Q4", f"Link-Ziel {host} liegt außerhalb der erlaubten Hosts "
                                f"({', '.join(ERLAUBTE_HOSTS)}) – prüfen, ob dieser Klickpfad "
                                "so gemeint ist", "warnung"))
    bekannte_slugs = {str(a.get("slug", "")) for a in (materiale or [])}
    for href in [h for h in hrefs if h.startswith("https")]:
        m = re.match(r"https?://franksfinanzcheck\.de/(posts|pillar)/([^/]+)/?$", href)
        if not m:
            continue
        bereich, slug = m.group(1), m.group(2)
        if slug in bekannte_slugs:
            continue
        if os.path.isdir(os.path.join(root, "content", bereich, slug)):
            continue
        funde.append(_regel("Q4", f"Link {href} zeigt auf ein Ziel, das es im Bestand nicht gibt "
                                  "und das nicht zu dieser Ausgabe gehört – im Postfach führt "
                                  "der Klick auf eine 404-Seite"))

    if https_ziele < 2:
        funde.append(_regel("Q4", f"{https_ziele} Zielseiten in der Mail – eine Spar-Ausgabe ohne "
                                  "Rechnung zum Öffnen ist keine"))
    if re.search(r"<a[^>]*>\s*</a>", html):
        funde.append(_regel("Q4", "Link ohne Text im E-Mail – Leser sehen nicht, wohin der Klick führt"))

    # ---- Q5 Bilder --------------------------------------------------------
    bilder = re.findall(r"<img[^>]*>", html)
    for b in bilder:
        fehlt = [p for p in ("alt=", "width=", "height=") if p not in b]
        if fehlt:
            funde.append(_regel("Q5", f"<img> fehlt {', '.join(fehlt)} – ohne alt verschwindet das "
                                      "Bild bei Bilder-Aus, ohne Maße springt das Layout"))
        m = re.search(r'src="([^"]+)"', b)
        if m and not m.group(1).startswith("https://"):
            funde.append(_regel("Q5", f"Bildquelle {m.group(1)!r} nicht absolut https – der "
                                      "Client kann es nicht laden"))
    if re.search(r"background-image\s*:", html):
        warnungen.append(_regel("Q5", "background-image im E-Mail – Outlook zeigt es nicht", "warnung"))
    if len(bilder) > 3:
        warnungen.append(_regel("Q5", f"{len(bilder)} Bilder – viele Clients laden sie nicht, "
                                "die Wort-Bild-Relation kippt Richtung Spam", "warnung"))

    # ---- Q6 Textmenge -----------------------------------------------------
    min_woerter = int(creative.get("min_woerter", 110))
    if len(worter) < min_woerter:
        funde.append(_regel("Q6", f"{len(worter)} Wörter sichtbarer Text – unter {min_woerter} "
                                  "liest das Postfach nach Werbung, nicht nach Substanz"))
    if bilder and len(worter) < 60 * len(bilder):
        warnungen.append(_regel("Q6", "zu wenig Text pro Bild – Bild-Mails landen im "
                                "Promotions-Tab und in Filtern", "warnung"))

    # ---- Q7 Ton -----------------------------------------------------------
    ganzer_text = f"{betreff}\n{pre}\n{rein}".lower()
    for wort in creative.get("verbotene_woerter", []):
        if wort and wort.lower() in ganzer_text:
            funde.append(_regel("Q7", f"Formulierung „{wort}“ steht in den verbotenen Wörtern "
                                      "der Konfiguration – Angstmache und Hype sind im "
                                      "Finanzversand beides: angreifbar und Spam-Signal"))
    ausrufe = betreff.count("!") + pre.count("!") + rein.count("!")
    max_a = int(creative.get("max_Ausrufezeichen", 2))
    if ausrufe > max_a:
        funde.append(_regel("Q7", f"{ausrufe} Ausrufezeichen (erlaubt {max_a}) – das Postfach "
                                  "schreit, der Filter merkt es"))
    geschrieen = [w for w in re.findall(r"\b[A-ZÄÖÜ]{5,}\b", f"{betreff} {rein}") if w not in GROSS_WEISS]
    if geschrieen:
        funde.append(_regel("Q7", f"Großbuchstaben-Wörter {geschrieen[:5]} – ALL CAPS ist in "
                                  "jeder Richtlinie ein Spam-Signal"))
    if re.search(r"€{3,}", ganzer_text):
        funde.append(_regel("Q7", "Währungszeichen-Stapel (€€€) – Wucherschrift"))

    # ---- Q8 Betreff -------------------------------------------------------
    reg = creative.get("betreff", {})
    min_l, max_l = int(reg.get("min_zeichen", 30)), int(reg.get("max_zeichen", 45))
    if not betreff:
        funde.append(_regel("Q8", "Betreff fehlt – ohne Betreff wird nicht zugestellt"))
    else:
        if len(betreff) > max_l:
            funde.append(_regel("Q8", f"Betreff {len(betreff)} Zeichen – über {max_l} schneidet "
                                      "die Mail-App auf dem Startschirm ab"))
        if re.match(r"^(re|aw|wg|fwd)\s*:", betreff, re.I):
            funde.append(_regel("Q8", "Antwortzusatz im Betreff eines Massenversands"))
        if "<" in betreff or "&" in betreff:
            funde.append(_regel("Q8", "HTML/Entities im Betreff – der Betreff ist Text, kein Markup"))
        marke = creative.get("marke_kurz", "")
        if marke and marke.lower() not in betreff.lower():
            warnungen.append(_regel("Q8", f"Markenname „{marke}“ nicht im Betreff – die "
                                    "Wiedererkennung ist der Grund, warum überhaupt geöffnet wird",
                                    "warnung"))

    # ---- Q9 Preheader -----------------------------------------------------
    p_reg = creative.get("preheader", {})
    p_min, p_max = int(p_reg.get("min_zeichen", 40)), int(p_reg.get("max_zeichen", 120))
    if not pre:
        funde.append(_regel("Q9", "Preheader fehlt – die Inbox zeigt den ersten Textrest "
                                  "(„Im Browser ansehen“) statt des Nutzens"))
    else:
        if len(pre) > p_max:
            funde.append(_regel("Q9", f"Preheader {len(pre)} Zeichen – über {p_max} wird er "
                                      "abgeschnitten und endet halbfertig"))
        if len(pre) < p_min:
            warnungen.append(_regel("Q9", f"Preheader {len(pre)} Zeichen – unter {p_min} füllt er "
                                    "die Vorschau nicht", "warnung"))
        schnitt = min(40, len(pre), len(betreff))
        if schnitt and pre[:schnitt].lower() == betreff[:schnitt].lower():
            funde.append(_regel("Q9", "Preheader wiederholt den Betreff – der zweite Satz ist "
                                      "verschenkt"))
        for klischee in PREHEADER_KLISCHEE:
            if klischee in pre.lower():
                funde.append(_regel("Q9", f"Preheader-Klischee „{klischee}“ – der Platz gehört "
                                          "dem Nutzen, nicht der Technik"))
        if "{{" in pre or "<" in pre:
            funde.append(_regel("Q9", "Platzhalter/Markup im Preheader – wird als Code ausgeliefert"))

    # ---- Q10 Rechtliches --------------------------------------------------
    fuss = next((b for b in blöcke if b.get("typ") == "fuss"), {})
    recht = e_mail.get("rechtliches", {})
    if not str(recht.get("anschrift", "")).strip():
        funde.append(_regel("Q10", "keine ladungsfähige Anschrift in der Fußzeile – "
                                  "geschäftsmäßiger Versand braucht sie (§ 5 DDG)"))
    if not str(recht.get("impressum_url", "")).startswith("https://"):
        funde.append(_regel("Q10", "Impressumslink fehlt oder ist kein https-Ziel"))
    if not str(recht.get("datenschutz_url", "")).startswith("https://"):
        funde.append(_regel("Q10", "Datenschutzlink fehlt – Art. 13 DSGVO gehört in jede Mail"))
    if "double-opt" not in (str(fuss.get("hinweis", "")) + html).lower():
        funde.append(_regel("Q10", "kein Double-Opt-In-Hinweis in der Fußzeile – der Nachweis "
                                  "der Anmeldung fehlt damit in der Mail selbst"))
    if re.search(r"(?i)(check24|awin|/go/|partnerlinks?|provision)", html) and \
            not str(recht.get("werbung_hinweis", "")).strip():
        funde.append(_regel("Q10", "Affiliate-/Partnerlinks in der Mail ohne Werbehinweis – "
                                  "Kennzeichnungspflicht (§ 5 Abs. 2 UWG, Rundfunk-Jugend-/"
                                  "Werberichtlinien)"))
    if "abmelden" not in html.lower():
        funde.append(_regel("Q10", "kein Wort „Abmelden“ am Link – eine eindeutige Beschriftung "
                                  "verlangt RFC 8058"))

    # ---- Q11 Kontrast -----------------------------------------------------
    kontrast_messung = studio.kontrast_pruefung(konf)
    for m in kontrast_messung:
        if not m["ok"]:
            funde.append(_regel("Q11", f"Kontrast {m['modus']}: {m['paar']} – "
                                      + (m.get("fehler") or
                                         f"{m['wert']}:1 statt {m['mindest']}:1 "
                                         f"({m.get('vorn')} auf {m.get('hinten')})")))

    # ---- Q12 Textalternative ---------------------------------------------
    for href in [h for h in hrefs if h.startswith("https")]:
        if href not in text:
            funde.append(_regel("Q12", f"Link {href} fehlt in der Textfassung – Leser ohne HTML "
                                      "bekommen die Rechnung nicht"))
    if "abmelden" not in text.lower():
        funde.append(_regel("Q12", "Textfassung ohne Abmeldemöglichkeit"))
    for b in blöcke:
        if b.get("typ") == "hero" and b.get("zahl") and b["zahl"] not in text:
            funde.append(_regel("Q12", f"Hero-Zahl {b['zahl']} fehlt in der Textfassung"))

    # ---- Q13 Mobil / tippbar ---------------------------------------------
    breite = int(e_mail.get("breite", 620) or 620)
    if f"max-width:{breite}px" not in re.sub(r"\s", "", html):
        funde.append(_regel("Q13", f"Container ohne max-width:{breite}px – in breiten Fenstern "
                                   "zerläuft die Mail über den Bildschirm"))
    # Die versteckte Preheader-Zeile arbeitet mit font-size:1px – das ist der
    # Standardtrick, keine gelesene Schrift. Für die Größenprüfung fällt sie raus.
    sichtbar = re.sub(r"<(\w+)[^>]*display:\s*none[^>]*>.*?</\1\s*>", " ", html, flags=re.S)
    groessen = sorted({float(m) for m in re.findall(r"font-size:\s*([0-9.]+)px", sichtbar)})
    if groessen and max(groessen) < 15:
        funde.append(_regel("Q13", f"größte Schrift {max(groessen):g}px – Fließtext unter 15 px "
                                   "ist auf dem Handy nicht lesbar"))
    if groessen and min(groessen) < 11:
        warnungen.append(_regel("Q13", f"kleinste Schrift {min(groessen):g}px – unter 11 px "
                                "liest niemand Rechtszeilen", "warnung"))
    zeilen = [float(m) for m in re.findall(r"line-height:\s*([0-9.]+)px", html)]
    if not any(z >= 40 for z in zeilen):
        warnungen.append(_regel("Q13", "kein Bedienelement mit Zeilenhöhe ≥ 40 px – die "
                                "Trefferfläche des Buttons ist zu klein für Finger", "warnung"))
    if 'name="viewport"' not in html:
        funde.append(_regel("Q13", "Viewport-Meta fehlt – Android skaliert die Mail auf "
                                   "Desktop-Breite und verkleinert jede Schrift"))

    # ---- Q14 Dokumentkopf -------------------------------------------------
    if not html.lstrip().lower().startswith("<!doctype html"):
        warnungen.append(_regel("Q14", "kein <!DOCTYPE html> – Outlook rutscht in den Quirks-"
                                "Modus mit anderen Tabellerbreiten", "warnung"))
    if 'lang="de"' not in html and "lang='de'" not in html and "lang=de" not in html:
        funde.append(_regel("Q14", "lang fehlt – Screenreader und Übersetzungsangebot brauchen "
                                   "die Sprache der Mail"))
    if re.search(r"""charset\s*=\s*["']?utf-8""", html, re.I) is None:
        funde.append(_regel("Q14", "kein Charset utf-8 – Umlaute werden zu Mojibake, und "
                                   "Outlook rät am Text"))
    for meta in ("color-scheme", "supported-color-schemes", "x-apple-disable-message-reformatting"):
        if meta not in html:
            warnungen.append(_regel("Q14", f"Meta {meta} fehlt – es steuert Dark Mode und "
                                    "Neuformatierung in Apple Mail", "warnung"))
    if "<title>" not in html:
        funde.append(_regel("Q14", "kein <title> – Webmailer zeigen es in Tab und Vorschau"))

    # ---- Q15 Betreff-Wiederholung ----------------------------------------
    verlauf = [h for h in ((zustand or {}).get("zuletzt_betreff") or []) if h]
    if betreff and betreff in verlauf:
        funde.append(_regel("Q15", f"Betreff „{betreff}“ wurde in einer der letzten {len(verlauf)} "
                                  "Ausgaben schon versandt – dieselbe Zeile zweimal ist der "
                                  "schnellste Abmeldegrund"))

    # ---- Q16 Zahlen-Belegpflicht -----------------------------------------
    material = materiale if materiale is not None else email.get("material", [])
    quelltexte = " ".join((a.get("quelle_text") or a.get("beschreibung") or a.get("titel") or "")
                          for a in material)
    beleg_zahlen = studio.zahlen_im_text(quelltexte)

    def unbelegt(wert: str) -> bool:
        ziffern = re.sub(r"\D", "", wert or "")
        return bool(ziffern) and ziffern not in beleg_zahlen

    for quelle, label in ((betreff, "Betreff"), (pre, "Preheader")):
        for m in studio.EURO_RE.finditer(quelle or ""):
            if unbelegt(m.group(1)):
                funde.append(_regel("Q16", f"{label} wirbt mit {m.group(0).strip()}, aber dieser "
                                          "Betrag steht in keinem Artikel dieser Ausgabe – eine "
                                          "Ersparnis ohne Beleg ist eine Behauptung"))
    for b in blöcke:
        if b.get("typ") == "hero" and b.get("zahl") and unbelegt(b["zahl"]):
            funde.append(_regel("Q16", f"Hero-Zahl {b['zahl']} hat keinen Beleg im Material – "
                                      "Belegstelle prüfen (zahl_aus_text liefert sie mit)"))
    for b in blöcke:
        if b.get("typ") == "hero" and b.get("zahl") and b.get("beleg"):
            if not re.search(re.escape(b["beleg"].split()[0]), quelltexte):
                warnungen.append(_regel("Q16", f"Hero-Beleg {b['beleg']!r} ist im Quelltext nicht "
                                        "als Wortsatz finden – Trenner geprüft, Wortlaut nicht",
                                        "warnung"))

    # ---- Q17 Blöcke -------------------------------------------------------
    artikel = [b for b in blöcke if b.get("typ") == "artikel"]
    max_anz = int(e_mail.get("max_artikel", 5))
    if len(artikel) > max_anz:
        funde.append(_regel("Q17", f"{len(artikel)} Artikelblöcke – mehr als {max_anz} liest "
                                   "abends niemand, und die Ausgabe überläuft"))
    if material:
        slugs = [a.get("slug") for a in material]
        if len(slugs) != len(set(slugs)):
            funde.append(_regel("Q17", "duplizierter Artikel in einer Ausgabe – derselbe Link "
                                      "zweimal wirkt wie ein Fehler der Pipeline"))
    for b in artikel:
        if not str(b.get("titel", "")).strip():
            funde.append(_regel("Q17", "Artikelblock ohne Titel"))
        if len(str(b.get("text", ""))) < 40:
            funde.append(_regel("Q17", f"Artikelblock „{str(b.get('titel', '?'))[:36]}“ hat keinen "
                                      "aussagekräftigen Text (unter 40 Zeichen)"))
        ziel = str(b.get("url", ""))
        if not (ziel.startswith("/posts/") or ziel.startswith("/pillar/") or ziel.startswith("http")):
            funde.append(_regel("Q17", f"Artikelblock zeigt auf {ziel!r} statt auf /posts/…"))

    # ---- Q18 Zeichensatz --------------------------------------------------
    for mo in MOJIBAKE:
        if mo in html or mo in text or mo in betreff:
            funde.append(_regel("Q18", f"Mojibake-Sequenz {mo!r} – Text wurde mit falschem "
                                      "Zeichensatz gelesen (Umlaute sind kaputt)"))
    if "&amp;amp;" in html:
        funde.append(_regel("Q18", "doppelt gemasert (&amp;amp;) – der Leser sieht &amp; im Text"))
    if re.search(r"&(?!amp;|lt;|gt;|quot;|#\d+;|nbsp;|zwnj;|hellip;)[A-Za-z]{2,6};", html):
        warnungen.append(_regel("Q18", "unbekannte HTML-Entity – Clients kennen sie nicht und "
                                "drucken den Namen", "warnung"))

    # ---- Q19 Tracking / Datenschutz --------------------------------------
    if e_mail.get("tracking_oeffnungen") is False:
        if re.search(r"(?i)(umami|matomo|google[- ]analytics|doubleclick|/open[?&]|track\.open)", html):
            funde.append(_regel("Q19", "Tracking-Anteil im E-Mail, obwohl `tracking_oeffnungen: "
                                      "false` konfiguriert ist – Öffnungsrate ohne Einwilligung ist "
                                      "der klassische Datenschutz-Fund im Newsletter"))
    if e_mail.get("ein_klick_abmeldung") is False:
        warnungen.append(_regel("Q19", "ein_klick_abmeldung: false – Google und Yahoo verlangen "
                                "seit 2024 RFC 8058 (List-Unsubscribe-Post) für Massenversand",
                                "warnung"))
    if re.search(r"(?i)list-unsubscribe", html):
        warnungen.append(_regel("Q19", "List-Unsubscribe im HTML statt im Header – den Header "
                                "schreibt der Anbieter; ein HTML-Klon verwirrt Filter", "warnung"))

    # ---- Q20 Absender -----------------------------------------------------
    absender = e_mail.get("absender", {})
    adresse = str(absender.get("email", ""))
    if "@" not in adresse:
        funde.append(_regel("Q20", f"Absender-Adresse {adresse!r} ist keine Adresse"))
    else:
        domain = adresse.split("@", 1)[1].lower()
        if not any(domain == h or domain.endswith("." + h) for h in EIGENE_ABSENDER_DOMAIN):
            warnungen.append(_regel("Q20", f"Absenderdomain {domain} ist nicht die eigene Domain – "
                                    "ohne eigene, authentifizierte Domain (SPF + DKIM + DMARC) "
                                    "landet Massenversand im Spam-Ordner", "warnung"))
    if not str(absender.get("name", "")).strip():
        funde.append(_regel("Q20", "kein Absendername – eine nacktere No-Reply-Adresse ist kein "
                                   "Vertrauenssignal"))
    antwort = str(e_mail.get("antwort_an", ""))
    if antwort and "@" not in antwort:
        funde.append(_regel("Q20", f"Antwortadresse {antwort!r} ist keine Adresse"))

    # ---- Q21 Kadenz -------------------------------------------------------
    # Der Versandvertrag ist ein Versprechen an den Leser: zwei Ausgaben,
    # Dienstag und Freitag. Zwei Fehlerarten sind teuer, und beide sind mit
    # einem Blick in den Kalender widerlegbar – eine Mail, die eine Kadenz
    # behauptet, die es nicht (mehr) gibt, und eine „Nächste Ausgabe“ an einem
    # Tag, an dem nie versendet wird. Beides kostet genau das, was der
    # Newsletter aufbaut: Verlässlichkeit.
    kadenz_texte = " ".join([rein, pre, betreff]).lower()
    for muster, grund in (("pro werktag", "ein Werktag-Versprechen"),
                          ("an jedem werktag", "ein Werktag-Versprechen"),
                          ("werktäglich", "ein Werktag-Versprechen"),
                          ("jeden werktag", "ein Werktag-Versprechen"),
                          ("mo–fr", "Versand Montag bis Freitag"),
                          ("mo-fr", "Versand Montag bis Freitag"),
                          ("mo. – fr.", "Versand Montag bis Freitag"),
                          ("montag bis freitag", "Versand Montag bis Freitag"),
                          ("jede woche fünf", "fünf Ausgaben pro Woche"),
                          ("1 mail/ tag", "ein Tages-Versprechen"),
                          ("1 mail/tag", "ein Tages-Versprechen")):
        if muster in kadenz_texte:
            funde.append(_regel("Q21", f"„{muster.strip()}“ in der Mail ist {grund} – der "
                                      f"Vertrag ({plan.versandtage_text()}, höchstens "
                                      f"{plan.MAX_PRO_WOCHE} pro Kalenderwoche) sagt etwas "
                                      "anderes; eine überholte Kadenz ist ein gebrochenes "
                                      "Versprechen im Postfach"))
    versprechen = str((konf.get("capture", {}) or {}).get("versprechen", ""))
    if versprechen.strip():
        fehlend = [plan.WOCHENTAGE[d] for d in plan.VERSANDTAGE
                   if plan.WOCHENTAGE_ADVERB[d] not in versprechen.lower()
                   and plan.WOCHENTAGE[d].lower() not in versprechen.lower()]
        if fehlend:
            funde.append(_regel("Q21", f"Das Versandversprechen nennt {fehlend} nicht – "
                                      f"„{versprechen}“ verspricht nicht, was der Kalender "
                                      "leistet"))
    datum = email.get("datum")
    if datum:
        try:
            tag = datetime.date.fromisoformat(str(datum)[:10])
        except ValueError:
            tag = None
        if tag:
            kopf = next((b for b in blöcke if b.get("typ") == "kopf"), {})
            if plan.ist_versandtag(tag) and \
                    plan.wochentag(tag).lower() not in str(kopf.get("zeile", "")).lower():
                funde.append(_regel("Q21", f"Der Kopf nennt den Versandtag "
                                          f"{plan.wochentag(tag)} nicht – die Mail "
                                          "beantwortet nicht, warum sie heute kommt"))
            fuss = next((b for b in blöcke if b.get("typ") == "fuss"), {})
            zeile = str(fuss.get("naechste", ""))
            if zeile:
                erkannt = plan.datum_lang_erkennen(zeile)
                soll = plan.naechster_termin(tag)
                if not erkannt:
                    funde.append(_regel("Q21", f"„{zeile}“ ist keine lesbare Terminzeile – "
                                              "eine Ansage ohne Datum ist keine Ansage"))
                elif erkannt["wochentag"] not in [plan.WOCHENTAGE[d] for d in plan.VERSANDTAGE]:
                    funde.append(_regel("Q21", f"„{zeile}“ kündigt {erkannt['wochentag']} an – "
                                              f"versendet wird {plan.versandtage_text()}"))
                elif (erkannt["tag"], erkannt["monat"]) != (soll.day, soll.month):
                    funde.append(_regel("Q21", f"„{zeile}“ – der Vertrag nennt als nächsten "
                                              f"Termin {plan.datum_lang(soll, mit_jahr=False)}"))

    # Das Minimum pro Modus wandert in die Messwerte: eine Zahl, die nur als
    # Fehlermeldung auftaucht, kann niemand mit der Vorwoche vergleichen – und
    # „grün, seit drei Wochen“ ist ohne Verlauf kein Beweis.
    minima = {}
    for modus in ("hell", "dunkel"):
        werte = [m["wert"] for m in kontrast_messung
                 if m.get("modus") == modus and m.get("wert", 0) > 1]
        minima["min_kontrast_" + modus] = round(min(werte), 2) if werte else 0.0

    score = max(0, 100 - 10 * len(funde) - 3 * len(warnungen))
    return {"bestanden": not funde, "score": score, "funde": funde, "warnungen": warnungen,
            "messwerte": {"html_bytes": groesse, "woerter": len(worter), "links": https_ziele,
                          "bilder": len(bilder), "betreff_zeichen": len(betreff),
                          "preheader_zeichen": len(pre), "artikel": len(artikel)} | minima,
            "regeln_geprueft": len(REGELN)}


# ------------------------------------------------------------------------- CLI
def _md(ergebnis: dict) -> str:
    zeilen = ["## 📬 Vor-Versand-Prüfung", "",
              f"**{ergebnis['score']}/100** · {ergebnis['regeln_geprueft']} Regeln · "
              f"{len(ergebnis['funde'])} Funde, {len(ergebnis['warnungen'])} Warnungen", "",
              "| Messwert | Wert |", "|---|---|"]
    for k, v in ergebnis["messwerte"].items():
        zeilen.append(f"| {k} | {v} |")
    for titel, liste in (("Funde", ergebnis["funde"]), ("Warnungen", ergebnis["warnungen"])):
        if liste:
            zeilen += ["", f"### {titel}", ""]
            zeilen += [f"- **{e['regel']}** {e['meldung']}" for e in liste]
    return "\n".join(zeilen) + "\n"


def _selftest() -> int:
    """Jede Regel wird mit einer gezielten Manipulation geprüft: was nicht gefunden
    wird, ist keine Wache. Kein Netz, kein Schreibzugriff, uhrfest."""
    fehler, zaehler = [], 0

    def pruefe_es(bedingung: bool, meldung: str) -> None:
        nonlocal zaehler
        if bedingung:
            zaehler += 1
        else:
            fehler.append(meldung)

    FIX = datetime.date(2026, 11, 17)         # Dienstag – bewusst ein festes Datum
    MAT = [{"slug": "a1", "titel": "Stromrechnung prüfen", "beschreibung": "240 € Ersparnis",
            "url": "/posts/a1/", "path": "", "datum": FIX.isoformat(), "pillar": "strom-sparen",
            "quelle_text": "Beim Wechsel lassen sich 240 € im Jahr sparen."},
           {"slug": "a2", "titel": "DSL-Wechselbonus sichern", "beschreibung": "120 € Bonus",
            "url": "/posts/a2/", "path": "", "datum": FIX.isoformat(), "pillar": "internet-dsl",
            "quelle_text": "Der Wechselbonus liegt bei 120 € und wird mit der ersten "
                           "Rechnung verrechnet."}]
    try:
        konf = studio.konfiguration(studio.BLOG_DIR)
        gut = studio.baue_email(MAT, datum=FIX, root=studio.BLOG_DIR)
        basis = pruefe(gut, konf=konf, materiale=MAT)
        pruefe_es(basis["bestanden"], "saubere Ausgabe besteht nicht: "
                  + " | ".join(f["meldung"] for f in basis["funde"]))
        pruefe_es(basis["messwerte"]["artikel"] == 2, "Messwerte zählen Artikel falsch")
        pruefe_es(basis["regeln_geprueft"] >= 20, "zu wenige Regeln registriert")
        pruefe_es(basis["score"] == 100, f"Score einer sauberen Ausgabe ist {basis['score']}")

        def kaputt(**aenderungen) -> dict:
            mail = dict(gut)
            mail.update(aenderungen)
            return pruefe(mail, konf=konf, materiale=MAT)

        def gefunden(code: str, ergebnis: dict) -> bool:
            return any(f["regel"] == code for f in ergebnis["funde"])

        pruefe_es(gefunden("Q1", kaputt(html="<html>" + "x" * 103_000 + "</html>")),
                  "Gmail-Clip-Grenze bleibt ungemeldet")
        pruefe_es(gefunden("Q1", kaputt(text="zu kurz")), "Textfassung unter der Mindestgröße fehlt als Fund")
        pruefe_es(gefunden("Q2", kaputt(html=gut["html"].replace("<table", "<div").replace('role="presentation"', "role=\"x\""))),
                  "Strukturfehler (kein Tabellen-Layout) bleibt unentdeckt")
        pruefe_es(gefunden("Q2", kaputt(html=gut["html"].replace("<body", "<script src=\"x.js\"></script><body"))),
                  "Script im E-Mail bleibt unentdeckt")
        pruefe_es(gefunden("Q2", kaputt(html=gut["html"].replace('style="margin:0;padding:0;',
                                                                  'style="display:flex;position:absolute;margin:0;'))),
                  "Flex/Absolute-Layout bleibt unentdeckt")
        pruefe_es(gefunden("Q3", kaputt(html=gut["html"].replace("{{unsubscribe}}", "{unsubscribe}"),
                                       text=gut["text"].replace("{{unsubscribe}}", "{unsubscribe}"))),
                  "Einzelklammer {unsubscribe} wird nicht als Alt-Syntax erkannt")
        pruefe_es(gefunden("Q3", kaputt(html=gut["html"].replace("{{unsubscribe}}", "{{ params.FOO }}"))),
                  "fremder Platzhalter bleibt ungeprüft")
        pruefe_es(gefunden("Q4", kaputt(html=gut["html"].replace("https://franksfinanzcheck.de",
                                                                 "http://franksfinanzcheck.de"))),
                  "http-Link wird durchgewinkt")
        pruefe_es(gefunden("Q4", kaputt(html=gut["html"].replace(
            "https://franksfinanzcheck.de/posts/a1/",
            "https://franksfinanzcheck.de/posts/gibt-es-nicht/"))),
                  "Link auf ein Ziel außerhalb des Bestands bleibt unbemerkt")
        pruefe_es(gefunden("Q5", kaputt(html=gut["html"] + '<img src="/bild.png">')),
                  "Bild ohne alt/Breite/Höhe besteht")
        pruefe_es(gefunden("Q6", kaputt(html=re.sub(r"<tr><td class=\"kachel.*?</td></tr>", "",
                                                    gut["html"], count=12, flags=re.S))),
                  "Textarmut besteht die Prüfung")
        pruefe_es(gefunden("Q7", kaputt(betreff="NUR HEUTE: 240 € GARANTIERT !!!")),
                  "Hype-Betreff besteht die Prüfung")
        pruefe_es(gefunden("Q8", kaputt(betreff="Re: kurz")), "Antwortzusatz/Kürze im Betreff fehlt als Fund")
        pruefe_es(gefunden("Q9", kaputt(preheader=gut["betreff"])),
                  "Preheader = Betreff wird nicht gemeldet")
        pruefe_es(gefunden("Q9", kaputt(preheader="")), "fehlender Preheader wird durchgewinkt")
        ohne_fuss = [b for b in gut["blocks"] if b["typ"] != "fuss"]
        pruefe_es(gefunden("Q10", kaputt(blocks=ohne_fuss,
                                        html=re.sub(r"Double-Opt-In", "", gut["html"]))),
                  "fehlender Rechtsfuß bleibt unentdeckt")
        k11 = json.loads(json.dumps(konf))
        k11["design"]["dunkel"]["text"] = "#404040"
        pruefe_es(gefunden("Q11", pruefe(gut, konf=k11, materiale=MAT)),
                  "mieser Kontrast besteht die Prüfung")
        pruefe_es(gefunden("Q12", kaputt(text="nur kurz")), "Textfassung ohne Links besteht")
        pruefe_es(gefunden("Q13", kaputt(html=gut["html"].replace("max-width:620px", "max-width:1200px"))),
                  "Containerbreite ohne Grenze bleibt unentdeckt")
        pruefe_es(gefunden("Q13", kaputt(html=gut["html"].replace('<meta name="viewport" '
                                                                  'content="width=device-width, initial-scale=1">', ""))),
                  "fehlende Viewport-Meta bleibt unentdeckt")
        pruefe_es(gefunden("Q14", kaputt(html=re.sub(r"<title>.*?</title>", "", gut["html"], flags=re.S))),
                  "fehlender Titel bleibt unentdeckt")
        pruefe_es(gefunden("Q15", pruefe(gut, konf=konf, materiale=MAT,
                                        zustand={"zuletzt_betreff": [gut["betreff"]]})),
                  "wiederverwendeter Betreff bleibt ungeprüft")
        pruefe_es(gefunden("Q16", kaputt(betreff="FranksFinanzcheck: 12.450 € heute prüfen")),
                  "unbelegte Ersparnis im Betreff wird durchgewinkt")
        hero_ohne_beleg = [dict(b) for b in gut["blocks"]]
        for b in hero_ohne_beleg:
            if b["typ"] == "hero":
                b["zahl"] = "9.999 €"
        pruefe_es(gefunden("Q16", kaputt(blocks=hero_ohne_beleg)),
                  "Hero-Zahl ohne Beleg bleibt unentdeckt")
        pruefe_es(gefunden("Q17", kaputt(blocks=gut["blocks"] + gut["blocks"] + gut["blocks"])),
                  "Blocküberlauf wird nicht gestoppt")
        pruefe_es(gefunden("Q18", kaputt(html=gut["html"].replace("FranksFinanzcheck", "FrÃ¤nks"))),
                  "Mojibake besteht die Prüfung")
        pruefe_es(gefunden("Q19", kaputt(html=gut["html"] +
                                        '<img src="https://franksfinanzcheck.de/open?t=1" width="1" height="1" alt="">')),
                  "Tracking-Pixel bei deaktiviertem Tracking bleibt unerkannt")
        k20 = json.loads(json.dumps(konf))
        k20["email"]["absender"]["email"] = "news@fremdversand.example"
        pruefe_es(any(w["regel"] == "Q20" for w in pruefe(gut, konf=k20, materiale=MAT)["warnungen"]),
                  "fremde Absenderdomain bleibt ohne Warnung")
        # Q21 Kadenz: vier Manipulationen, jede muss den richtigen Code liefern
        pruefe_es(gefunden("Q21", kaputt(html=gut["html"].replace(
            "Zweimal pro Woche", "Eine Mail pro Werktag"))),
                  "überholtes Werktags-Versprechen bleibt unentdeckt")
        kopf_ohne_tag = [dict(b) for b in gut["blocks"]]
        for b in kopf_ohne_tag:
            if b["typ"] == "kopf":
                b["zeile"] = "17.11.2026 · Ausgabe 47/2026"
        pruefe_es(gefunden("Q21", kaputt(blocks=kopf_ohne_tag)),
                  "Kopf ohne Versandtag bleibt unentdeckt")
        fuss_falsch = [dict(b) for b in gut["blocks"]]
        for b in fuss_falsch:
            if b["typ"] == "fuss":
                b["naechste"] = "Nächste Ausgabe: Mittwoch, 18. November"
        pruefe_es(gefunden("Q21", kaputt(blocks=fuss_falsch)),
                  "unmöglicher nächster Versandtag bleibt unentdeckt")
        fuss_verrutscht = [dict(b) for b in gut["blocks"]]
        for b in fuss_verrutscht:
            if b["typ"] == "fuss":
                b["naechste"] = "Nächste Ausgabe: Freitag, 27. November"
        pruefe_es(gefunden("Q21", kaputt(blocks=fuss_verrutscht)),
                  "verschobener nächster Versandtag bleibt unentdeckt")
        k21 = json.loads(json.dumps(konf))
        k21["capture"]["versprechen"] = "Jede Woche neue Spartipps."
        pruefe_es(gefunden("Q21", pruefe(gut, konf=k21, materiale=MAT)),
                  "Versandversprechen ohne Versandtage bleibt unentdeckt")
        pruefe_es(all(m["wert"] > 0 for m in studio.kontrast_pruefung(konf)),
                  "Kontrastmessung lieferte 0 (Rollenfehler)")
        weiter = pruefe(studio.baue_email(MAT, datum=FIX + datetime.timedelta(days=97 * 3),
                                         root=studio.BLOG_DIR), konf=konf, materiale=MAT)
        pruefe_es(weiter["bestanden"], "Selbsttest ist nicht uhrfest: "
                  + " | ".join(f["meldung"] for f in weiter["funde"]))
        pruefe_es(pruefe({"html": "", "text": "", "betreff": "", "preheader": "", "blocks": []},
                         konf=konf, materiale=[])["bestanden"] is False,
                  "leere Eingabe besteht die Prüfung")
    except Exception as exc:                                   # noqa: BLE001
        import traceback
        fehler.append(f"Ausführung: {exc.__class__.__name__}: {exc}\n" + traceback.format_exc()[-600:])
    if fehler:
        print("🛑 newsletter_qa-Selbsttest FEHLGESCHLAGEN:")
        for f in fehler:
            print("  -", f)
        return 2
    print(f"✅ QA-Selbsttest: {zaehler} Fälle grün (21 Regeln, jede Manipulation gefunden, "
          "uhrfest, kein Netz, keine Schreibrechte).")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Vor-Versand-Prüfung des Newsletters (Q1..Q21)")
    ap.add_argument("--root", default=BLOG_DIR)
    ap.add_argument("--build", action="store_true", help="Ausgabe aus dem Bestand bauen und prüfen")
    ap.add_argument("--days", type=int, default=1)
    ap.add_argument("--datei", default="", help="zu prüfende HTML-Datei (oder Glob)")
    ap.add_argument("--text", default="", help="zugehörige Textfassung")
    ap.add_argument("--betreff", default="")
    ap.add_argument("--preheader", default="")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--md", action="store_true", help="Markdown für die CI-Summary")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    root = os.path.abspath(args.root)
    try:
        konf = studio.konfiguration(root)
    except SystemExit as exc:
        print(exc)
        return 2
    zustand = {}
    try:
        zustand = json.loads(studio._read(os.path.join(root, "data", "newsletter_state.json")) or "{}")
    except json.JSONDecodeError:
        pass
    if args.build:
        material = studio.material_aus_artikel(root, studio._artikel_suchen(root, args.days))
        if not material:
            print("📬 QA: kein Material im Zeitraum – nichts zu prüfen (kein Fund, kein Versand).")
            return 0
        email = studio.baue_email(material, root=root)
        ergebnis = pruefe(email, konf=konf, materiale=material, zustand=zustand)
    elif args.datei:
        pfade = sorted(glob.glob(args.datei))
        if not pfade:
            print(f"❌ QA: {args.datei} nicht lesbar – Prüfung ausgefallen, nicht bestanden")
            return 2
        email = {"html": studio._read(pfade[0]), "text": studio._read(args.text) if args.text else "",
                 "betreff": args.betreff, "preheader": args.preheader, "blocks": [], "material": []}
        ergebnis = pruefe(email, konf=konf, materiale=[], zustand=zustand)
    else:
        ap.print_help()
        return 2
    if args.json:
        print(json.dumps(ergebnis, ensure_ascii=False, indent=2))
    elif args.md:
        print(_md(ergebnis))
    else:
        print(f"Vor-Versand-Prüfung · {ergebnis['score']}/100 · {ergebnis['regeln_geprueft']} Regeln")
        for f in ergebnis["funde"]:
            print(f"  ❌ [{f['regel']}] {f['meldung']}")
        for w in ergebnis["warnungen"]:
            print(f"  ⚠ [{w['regel']}] {w['meldung']}")
        mess = " · ".join(f"{k}={v}" for k, v in ergebnis["messwerte"].items())
        print(f"  · {mess}")
        if ergebnis["bestanden"]:
            print("  ✅ Versand frei – die Ausgabe besteht alle harten Regeln.")
    return 0 if ergebnis["bestanden"] else 1


if __name__ == "__main__":
    sys.exit(main())
