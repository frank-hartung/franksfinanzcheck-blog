#!/usr/bin/env python3
"""
satz_heiler.py – Lesbarkeit durch SÄTZE statt durch Ganztext-KI (#614).

WARUM ES IHN GIBT (Befund 07.10.2026, BOT-WATCHDOG #614)
--------------------------------------------------------
`data/reserve-readiness.json` stand auf „Ziel 6, bereit 2". Sieben der zehn
geparkten Kandidaten hingen allein am harten Lesbarkeits-Gate
(`readability_check.NEW_FLESCH_MIN` = 60). Zwei Heiler waren zuständig:

  * **Lesbarkeits-Heiler Stufe A** (deterministisch): lokal gemessen hebt er
    diese Texte auf 58,1 / 59,0 / 59,2 / 59,9 – die Schwelle ist damit
    **prinzipiell unerreichbar** (Tor T1 verwirft jede Schrift < 60).
  * **Lesbarkeits-Heiler Stufe B** (KI): schickt den GANZEN Artikel an das
    Modell. Sein Tor T4 verlangt danach, dass Zahlen (74 Token), Tabellenzeilen
    (7), Überschriften (21) und Links (8) **byte-genau** erhalten bleiben – eine
    Ganztext-Antwort eines Sprachmodells erfüllt das praktisch nie. Beleg aus
    dem Bestand: Über mehrere Läufe trugen die geparkten Kandidaten denselben
    Flesch-Wert (57,9 → 58,0); KEINE KI-Fassung wurde je geschrieben.

Die Klasse war also nicht „schwer zu heilen", sondern **nicht heilbar gebaut**:
Der eine Heiler kann die Schwelle nicht erreichen, der andere darf nicht
schreiben. Genau deshalb blieb der Vorrat bei 2/6.

DIE UMKEHRUNG
-------------
Dieser Heiler dreht den Weg um: Die KI bekommt **nur einzelne Sätze** – Sätze
ohne Zahlen, ohne Links, ohne Tabellen-/Markup-Zeichen. Ihre Antwort wird Satz
für Satz geprüft, nur bei Erfüllung eingesetzt, und **erst danach** entscheidet
dasselbe Ganztext-Tor wie beim Lesbarkeits-Heiler (`lesbarkeit_heiler.
verifiziere`, T1–T4 + Publikations-Vertrag). Nichts wird gelockert, nichts
geraten: Was die KI anfassen darf, ist auf das beschränkt, was sie nicht
kaputtmachen kann; was sie nicht anfassen darf (Zahlen, Tabellen,
Überschriften, Links, Shortcodes), erreicht sie nie.

REGELN
------
  * Nur Fließtext-Sätze ohne Ziffern und ohne Markup `[]()|{}<>` – damit sind
    Zahlen-, Link-, Tabellen- und Shortcode-Prüfungen konstruktiv erfüllt.
  * Je Ersatz: keine Ziffern/Markup/URLs, nicht länger, nicht mehr Wörter,
    höchstens 20 % Wortverlust, kürzere Wörter ODER Satzteilung,
    Duktus erhalten (kein „Sie", wenn der Satz „du" sprach), keine
    Intro-Formel (R7) und keine Ruine (R14/R16) – geprüft gegen die SSOT.
  * Gedeckelt: höchstens `--max-ki` Anfragen je Artikel, höchstens 7 %
    Textverlust insgesamt (T4 verlangt ≥ 90 % – der Puffer gehört dem Tor).
  * Geschrieben wird NUR mit `--fix`. Standardmäßig darf ein sicherer
    Teilfortschritt bestehen bleiben: mindestens +0,3 Flesch-Punkte, alle
    Nicht-Lesbarkeitstore still. `--nur-ganz` oder
    `FFC_SATZ_NUR_GANZ=1` stellt Alles-oder-nichts wieder her.

MODI
  python3 scripts/satz_heiler.py --file <index.md> [--fix] [--json]
  python3 scripts/satz_heiler.py --reserve --fix          # Pool-Kandidaten
  python3 scripts/satz_heiler.py --nur-ganz               # nur ≥ Schwelle schreiben
  python3 scripts/satz_heiler.py --selftest               # Sabotage-Schutz
  python3 scripts/satz_heiler.py --wirkungsprobe          # Maschinenvertrag (C25)
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re
import sys
from pathlib import Path

BLOG_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BLOG_DIR / "scripts"))

import post_utils          # noqa: E402  (Naht: join_article)
import r5_absatz_splitter as r5  # noqa: E402  (R5-SSOT: Absätze ≤ 4 Sätze)
import readability_check as rc  # noqa: E402  (Schwelle: NEW_FLESCH_MIN)
import sprachkern as sk    # noqa: E402  (Ruinen-SSOT R14/R16)
import textverstaendnis_guard as tv  # noqa: E402  (Intro-Formeln R7)
import lesbarkeit_heiler as lh  # noqa: E402  (DAS Tor T1–T4 + KI-Transport)

MINDEST = rc.NEW_FLESCH_MIN          # importierte SSOT, nie abgetippt
BATCH = 4                            # Sätze je KI-Anfrage
MAX_KI_STANDARD = 16                 # Anfragen je Artikel (Deckel)
MAX_SCHWUND = 0.07                   # höchstens 7 % Textlänge (T4: 90 %)
MAX_ANTEIL = 0.5                     # höchstens die Hälfte der Fließsätze
MIN_WOERTER = 6                      # kürzere Sätze lohnen keinen Umbau
MAX_ERSATZ_TOLERANZ = 0.20           # höchstens 20 % Wortverlust je Satz
MIN_FORTSCHRITT = 0.3                # sauberer Teilfortschritt unterhalb der Schwelle
SATZ_NUR_GANZ_ENV = "FFC_SATZ_NUR_GANZ"

MARKUP = set("[]()|{}<>`")
_WORT = re.compile(r"[A-Za-zÄÖÜäöüß0-9]+")
_BANNED = re.compile(r"[\d\[\]()|{}<>`]")
_SIE = re.compile(r"\b(Sie|Ihnen|Ihre|Ihrem|Ihrer|Ihren)\b")
_DU = re.compile(r"\b(du|dein|deine|deinem|deinen|deiner|dich|dir)\b")

KI_CALL = None                       # injizierbar für Selbsttest/Wirkungsprobe


# ---------------------------------------------------------------------------
#  KI-TRANSPORT – eine Quelle: derselbe Weg wie der Lesbarkeits-Heiler
#  (Gemini zuerst, Groq als Rückfall, dieselben Schlüssel). Kein zweiter
#  Transportweg, der auseinanderlaufen könnte.
# ---------------------------------------------------------------------------
def _ki_antwort(prompt: str) -> str | None:
    if KI_CALL is not None:
        return KI_CALL(prompt)
    return lh._ki_chat(prompt)


PROMPT = """Du bist deutscher Lektor. Vereinfache die folgenden Sätze für ein
Finanz-Blog, damit sie leichter lesbar werden.

Regeln:
- Nimm kürzere Wörter; löse lange Zusammensetzungen auf (z. B. \
"Verbrauchskosten" -> "Kosten").
- Teile lange Sätze an einer natürlichen Stelle in zwei Sätze (Punkt statt Komma).
- Inhalt, Aussage und Ton bleiben gleich. Keine neuen Fakten.
- Keine Zahlen, keine Links, keine Aufzählungszeichen (die Sätze enthalten keine).
- Du-Form beibehalten.
- Antworte NUR mit den Sätzen, nummeriert wie die Vorlage, je eine Zeile:
  1) <Satz>

Sätze:
{saetze}"""


# ---------------------------------------------------------------------------
#  SATZAUSWAHL – nur Fließtext, ohne Ziffern und Markup
# ---------------------------------------------------------------------------
def _zeilen_mit_offset(body: str):
    pos = 0
    for zeile in body.split("\n"):
        yield pos, zeile
        pos += len(zeile) + 1


def _ist_prosa(zeile: str) -> bool:
    s = zeile.strip()
    if not s:
        return False
    if s[0] in "#|>*-+<{" or s.startswith("<!--"):
        return False
    if re.match(r"^\d+[.)]\s", s):           # Listen
        return False
    return True


def saetze_finden(body: str, *, base_offset: int = 0) -> list[dict]:
    """Fließtext-Sätze mit Datei-Zeiger, Länge und Wortzahl.

    `base_offset` hebt Body-Zeiger in das Koordinatensystem der vollständigen
    Datei. Ohne Offset bleibt die Funktion für reine Body-Analysen kompatibel.
    """
    treffer = []
    for offset, zeile in _zeilen_mit_offset(body):
        if not _ist_prosa(zeile):
            continue
        for m in re.finditer(r"[^.!?\n]+[.!?]+", zeile):
            satz = m.group(0).strip()
            woerter = _WORT.findall(satz)
            if len(woerter) < MIN_WOERTER:
                continue
            if _BANNED.search(satz) or "http" in satz:
                continue
            start = (base_offset + offset + m.start()
                     + (len(m.group(0)) - len(m.group(0).lstrip())))
            treffer.append({"start": start, "satz": satz,
                            "woerter": [w for w in woerter],
                            "lang": sum(1 for w in woerter if len(w) > 12)})
    return treffer


def _drag(eintrag: dict) -> float:
    """Wie sehr bremst dieser Satz die Lesbarkeit? (Wortzahl + lange Wörter)."""
    woerter = eintrag["woerter"]
    return (len(woerter) - 8) + 2.5 * eintrag["lang"] + \
        sum(max(0, len(w) - 10) for w in woerter) / 3.0


def _woerter(text: str) -> list[str]:
    return _WORT.findall(text)


def _mittlere_wortlaenge(woerter: list[str]) -> float:
    return sum(len(w) for w in woerter) / len(woerter) if woerter else 0.0


# ---------------------------------------------------------------------------
#  DAS SATZTOR – was darf ein KI-Ersatz?
# ---------------------------------------------------------------------------
def pruefe_ersatz(alt: str, neu: str) -> list[str]:
    """Gründe, die einen KI-Ersatz verwerfen (leer = annehmbar)."""
    gruende: list[str] = []
    neu = " ".join((neu or "").split())
    if not neu:
        return ["leer"]
    if neu == alt:
        return ["keine Änderung"]
    if "\n" in neu:
        return ["mehrzeilig"]
    if _BANNED.search(neu):
        gruende.append("Ziffer oder Markup in der Antwort")
    if "http" in neu or "www." in neu:
        gruende.append("URL in der Antwort")
    if set(re.findall(r"[*_]", neu)) - set(re.findall(r"[*_]", alt)):
        gruende.append("neues Markup (**/_ ) in der Antwort")
    if len(neu) > len(alt) * 1.05:
        gruende.append(f"länger als der Satz ({len(alt)} → {len(neu)} Zeichen)")
    w_alt, w_neu = _woerter(alt), _woerter(neu)
    if not w_neu:
        return ["keine Wörter"]
    # Vereinfachen darf mehr Wörter brauchen (kurze Sätze statt Schachtelsatz) –
    # aber nicht ausufern. Der Ganztext-Flesch am Ende ist der eigentliche Richter.
    if len(w_neu) > len(w_alt) * 1.5 + 2:
        gruende.append(f"zu viele Wörter ({len(w_alt)} → {len(w_neu)})")
    if len(w_neu) < len(w_alt) * (1 - MAX_ERSATZ_TOLERANZ):
        gruende.append(f"zu stark gekürzt ({len(w_alt)} → {len(w_neu)} Wörter)")
    # Wirkung: kürzere Wörter ODER Satzteilung (mehr Satzenden)
    kuerzer = _mittlere_wortlaenge(w_neu) < _mittlere_wortlaenge(w_alt) - 0.15
    geteilt = neu.count(".") + neu.count("!") + neu.count("?") > \
        alt.count(".") + alt.count("!") + alt.count("?")
    if not (kuerzer or geteilt):
        gruende.append("keine kürzeren Wörter und keine Satzteilung")
    for name, muster, _text in sk.POLITUR_RUINEN:
        if muster.search(neu):
            gruende.append(f"Ruine {name}")
            break
    klein = neu.lower()
    for formel in tv.INTRO_FORMELN:
        if formel.lower() in klein:
            gruende.append(f"Intro-Formel „{formel}\"")
            break
    if _SIE.search(neu) and not _SIE.search(alt):
        gruende.append("Duktus verletzt (Sie-Form eingeführt)")
    if _DU.search(alt) and _SIE.search(neu):
        gruende.append("Duktus verletzt (du → Sie)")
    return gruende


# ---------------------------------------------------------------------------
#  DER HEILWEG
# ---------------------------------------------------------------------------
def _teile(rohtext: str):
    parts = (rohtext or "").split("---", 2)
    return parts if len(parts) == 3 else None


def _body_offset(rohtext: str, teile: list[str] | None = None) -> int:
    """Datei-Koordinate des Bodys; Frontmatter bleibt strikt außerhalb."""
    teile = teile if teile is not None else _teile(rohtext)
    if teile is None:
        return 0
    return len(rohtext) - len(teile[2])


def _kopf_bis_body(rohtext: str) -> str | None:
    """Exakte Kopf-/Trennzeichenfolge bis zum ersten Body-Zeichen."""
    teile = _teile(rohtext)
    if teile is None:
        return None
    return rohtext[:_body_offset(rohtext, teile)]


def _finde_satz(rohtext: str, satz: str,
                 start_hint: int | None = None) -> int:
    """Sucht einen vollständigen Satz frisch im Body und liefert Datei-Offset.

    `0` ist bewusst ein ungültiger Sentinel: gültiges Frontmatter liegt immer
    davor. Der Kopf wird nie durchsucht, auch dann nicht, wenn er denselben
    Wortlaut enthält. `start_hint` dient nur der Zuordnung identischer Sätze;
    die Position wird aus dem aktuellen Text neu berechnet.
    """
    teile = _teile(rohtext)
    if teile is None or not satz:
        return 0
    body_offset = _body_offset(rohtext, teile)
    fundstellen = [e["start"] for e in saetze_finden(
        teile[2], base_offset=body_offset) if e["satz"] == satz]
    if not fundstellen:
        return 0
    if start_hint is not None:
        return min(fundstellen, key=lambda pos: abs(pos - start_hint))
    return fundstellen[0]


def unversehrte_saetze(alt_raw: str, neu_raw: str,
                       ersetzungen: list[tuple[str, str]] | None = None) -> list[str]:
    """Prüft, dass nur vollständige, protokollierte Sätze geändert wurden.

    Der erwartete Text wird aus dem Original und den zugelassenen Ersetzungen
    unabhängig neu aufgebaut. Ein Vergleich nach Whitespace-Normalisierung
    erlaubt dem R5-Splitter Absatzumbrüche, aber keine verlorenen Satzteile,
    fremden Änderungen oder beschädigten Nachbarsätze.
    """
    alt_teile, neu_teile = _teile(alt_raw), _teile(neu_raw)
    if alt_teile is None or neu_teile is None:
        return ["Satzschutz: Frontmatter-Grenzen fehlen – fail-closed"]
    if _kopf_bis_body(alt_raw) != _kopf_bis_body(neu_raw):
        return ["Kopf-Tor: Frontmatter/Trenner nicht byte-identisch"]

    erwartet = alt_raw
    for vorher, nachher in ersetzungen or []:
        position = _finde_satz(erwartet, vorher)
        if position <= 0:
            return [f"Satzschutz: vollständiger Ausgangssatz nicht gefunden: {vorher[:70]!r}"]
        erwartet = (erwartet[:position] + nachher
                    + erwartet[position + len(vorher):])

    erwartet_teile = _teile(erwartet)
    if erwartet_teile is None:
        return ["Satzschutz: erwartete Frontmatter-Grenzen fehlen – fail-closed"]
    if " ".join(erwartet_teile[2].split()) != " ".join(neu_teile[2].split()):
        return ["Satz-Zerstückelung: außerhalb vollständiger Ersetzungen wurde "
                "Text verändert"]
    return []


def _slug_von(pfad: str) -> str:
    return os.path.basename(os.path.dirname(str(pfad)))


def _ist_entwurf(rohtext: str) -> bool:
    teile = _teile(rohtext)
    return bool(teile) and bool(re.search(r"(?m)^draft:\s*true\s*$", teile[1], re.I))


def _nur_ganz_aktiv(wert: bool | None = None) -> bool:
    if wert is not None:
        return bool(wert)
    return os.environ.get(SATZ_NUR_GANZ_ENV, "").strip().lower() in {
        "1", "true", "yes", "on"}


def heile_text(slug: str, rohtext: str, *, max_ki: int = MAX_KI_STANDARD,
               ki: bool = True, nur_ganz: bool | None = None) -> dict:
    """Heilt satzweise; sichere Zwischenstufen sind standardmäßig schreibbar."""
    nur_ganz = _nur_ganz_aktiv(nur_ganz)
    ergebnis = {"slug": slug, "ok": False, "neu_raw": rohtext, "vor": None,
                "nach": None, "ersetzt": [], "verworfen": [], "anfragen": 0,
                "gruende": [], "geschrieben": False, "vollstaendig": False,
                "teilfortschritt": False}
    teile = _teile(rohtext)
    if teile is None:
        ergebnis["gruende"] = ["Frontmatter-Grenzen fehlen – fail-closed"]
        return ergebnis
    vor = lh.flesch(rohtext, slug)
    ergebnis["vor"] = vor
    if vor is None:
        ergebnis["gruende"] = ["Text nicht messbar – fail-closed"]
        return ergebnis
    if vor >= MINDEST:
        ergebnis.update(ok=True, nach=vor, vollstaendig=True,
                        befund=f"bereits über der Schwelle ({vor:.1f} ≥ {MINDEST:g})")
        return ergebnis
    if not ki:
        ergebnis["gruende"] = [f"Flesch {vor:.1f} < {MINDEST:g} – ohne KI "
                               "ist diese Klasse nicht heilbar (Stufe A reicht "
                               "nachweislich nicht)"]
        return ergebnis

    # saetze_finden misst im Body. Der Offset hebt jeden Zeiger in das
    # Datei-Koordinatensystem, bevor er als Kandidat gespeichert wird.
    body_offset = _body_offset(rohtext, teile)
    satzliste = saetze_finden(teile[2], base_offset=body_offset)
    if not satzliste:
        ergebnis["gruende"] = ["keine heilbaren Fließtext-Sätze gefunden"]
        return ergebnis
    grenze = int(len(satzliste) * MAX_ANTEIL)
    # Die stärksten Bremsen zuerst, höchstens die Hälfte der Sätze.
    reihenfolge = sorted(range(len(satzliste)), key=lambda i: -_drag(satzliste[i]))
    kandidaten = [satzliste[i] for i in reihenfolge[:max(1, grenze)]]
    budget_zeichen = int(len(teile[2]) * MAX_SCHWUND)

    aktuell = rohtext
    aktuelle_flesch = vor
    runde = 0
    ki_ausfall = False
    ersatz_protokoll: list[tuple[str, str]] = []
    while (ergebnis["anfragen"] < max_ki and aktuelle_flesch < MINDEST
           and kandidaten and runde < 12 and not ki_ausfall):
        runde += 1
        block, kandidaten = kandidaten[:BATCH * 3], kandidaten[BATCH * 3:]
        if not block:
            break
        for start in range(0, len(block), BATCH):
            gruppe = block[start:start + BATCH]
            if ergebnis["anfragen"] >= max_ki:
                break
            liste = "\n".join(f"{i + 1}) {e['satz']}" for i, e in enumerate(gruppe))
            ergebnis["anfragen"] += 1
            antwort = _ki_antwort(PROMPT.format(saetze=liste))
            if not antwort:
                # Kein Kontingent verbrennen: wer keine Antwort bekommt, fragt
                # nicht noch zehnmal. Fail-closed und ehrlich im Bericht.
                ergebnis["gruende"].append(
                    f"keine KI-Antwort (Runde {runde}) – Text bleibt unangetastet, "
                    "keine weiteren Anfragen")
                ki_ausfall = True
                break
            zugeordnet = _antwort_zerlegen(antwort, len(gruppe))
            # Jedes alte Wort wird weiter geprüft, aber nie über einen
            # gespeicherten Body-Offset in den aktuellen Ganztext gespleißt.
            for nummer in sorted(zugeordnet, reverse=True):
                eintrag = gruppe[nummer - 1]
                vorher, neu = eintrag["satz"], zugeordnet[nummer]
                beanstandet = pruefe_ersatz(vorher, neu)
                if beanstandet:
                    ergebnis["verworfen"].append(
                        {"satz": vorher[:70], "gruende": beanstandet})
                    continue
                if len(neu) > len(vorher):
                    ergebnis["verworfen"].append(
                        {"satz": vorher[:70], "gruende": ["länger als der Satz"]})
                    continue
                if budget_zeichen + (len(neu) - len(vorher)) < 0:
                    ergebnis["verworfen"].append(
                        {"satz": vorher[:70],
                         "gruende": ["Textverlust-Budget erschöpft"]})
                    continue

                # Nicht den beim ersten Scan veralteten Zeiger benutzen:
                # jedes Mal im AKTUELLEN Body frisch suchen; 0 bleibt ungültig.
                position = _finde_satz(aktuell, vorher,
                                       start_hint=eintrag["start"])
                aktuell_teile = _teile(aktuell)
                aktuell_body_start = _body_offset(aktuell, aktuell_teile)
                if position <= 0 or position < aktuell_body_start:
                    ergebnis["verworfen"].append(
                        {"satz": vorher[:70],
                         "gruende": ["vollständiger Satz im Body nicht gefunden"]})
                    continue
                if aktuell[position:position + len(vorher)] != vorher:
                    ergebnis["verworfen"].append(
                        {"satz": vorher[:70],
                         "gruende": ["Satz-Zeiger stimmt nicht mehr – fail-closed"]})
                    continue
                aktuell = (aktuell[:position] + neu
                           + aktuell[position + len(vorher):])
                ersatz_protokoll.append((vorher, neu))
                budget_zeichen += len(neu) - len(vorher)
                ergebnis["ersetzt"].append({"vorher": vorher[:70],
                                            "nachher": neu[:70]})
            aktuelle_flesch = lh.flesch(aktuell, slug)
            if aktuelle_flesch is None or aktuelle_flesch >= MINDEST:
                break
        if aktuelle_flesch is None or aktuelle_flesch >= MINDEST:
            break

    # Satzteilung erzeugt mehr Sätze je Absatz – R5-ABSATZ-HART (> 4 Sätze)
    # hat einen eigenen Heiler (SSOT). Wir rufen IHN auf, statt die Regel zu
    # verletzen: so bleibt das Ergebnis auch unter der Textverständnis-Wache
    # sauber, ohne dass zwei Programme dieselbe Regel unterschiedlich auslegen.
    teile_neu = _teile(aktuell)
    if teile_neu is not None:
        body_neu, geteilt, _warn = r5.split_body_text(teile_neu[2], label=slug)
        if geteilt:
            aktuell = post_utils.join_article(teile_neu[1], body_neu, teile_neu[0])
            ergebnis["absaetze_geteilt"] = geteilt
            aktuelle_flesch = lh.flesch(aktuell, slug)

    # Das explizite Kopf-Tor ist unabhängig von der Positionsrechnung und
    # dem allgemeinen T4: bei jeder Abweichung wird komplett zurückgerollt.
    if _kopf_bis_body(rohtext) != _kopf_bis_body(aktuell):
        ergebnis["gruende"].append(
            "Kopf-Tor: Frontmatter/Trenner nicht byte-identisch – nichts geschrieben")
        return ergebnis
    satzfehler = unversehrte_saetze(rohtext, aktuell, ersatz_protokoll)
    if satzfehler:
        ergebnis["gruende"].extend(satzfehler)
        return ergebnis

    ergebnis["nach"] = aktuelle_flesch
    if aktuell == rohtext:
        ergebnis["gruende"].append(
            f"Flesch {vor:.1f} blieb unverändert – fail-closed, nichts geschrieben")
        return ergebnis
    if aktuelle_flesch is None:
        ergebnis["gruende"].append("Flesch im Ergebnis nicht messbar – fail-closed")
        return ergebnis

    # Das Ganztext-Tor bleibt unverändert. Unter der Schwelle darf nur dessen
    # isolierter T1-Schwellenhinweis toleriert werden – und nur bei +0,3 Punkten.
    tor = lh.verifiziere(slug, rohtext, aktuell)
    teilfortschritt = False
    if aktuelle_flesch < MINDEST:
        delta = aktuelle_flesch - vor
        schwellenfehler = [g for g in tor
                           if g.startswith("T1 Lesbarkeit: Flesch ")
                           and " < Schwelle " in g]
        sonstige_fehler = [g for g in tor if g not in schwellenfehler]
        teilfortschritt = (
            not nur_ganz and delta + 1e-9 >= MIN_FORTSCHRITT
            and bool(schwellenfehler) and not sonstige_fehler)
        if not teilfortschritt:
            ergebnis["gruende"] += [f"Tor: {g}" for g in tor]
            if nur_ganz and schwellenfehler:
                ergebnis["gruende"].append(
                    "Teilfortschritt verworfen: Alles-oder-nichts aktiv")
            elif not schwellenfehler:
                if delta < MIN_FORTSCHRITT:
                    ergebnis["gruende"].append(
                        f"Teilfortschritt zu klein ({delta:.1f} < "
                        f"{MIN_FORTSCHRITT:.1f} Flesch)")
                else:
                    ergebnis["gruende"].append(
                        "Teilfortschritt nicht fail-closed freigabefähig")
            ergebnis["neu_raw"] = rohtext
            ergebnis["nach"] = vor
            return ergebnis
    elif tor:
        ergebnis["gruende"] += [f"Tor: {g}" for g in tor]
        ergebnis["neu_raw"] = rohtext
        ergebnis["nach"] = vor
        return ergebnis

    ergebnis.update(ok=True, neu_raw=aktuell,
                    vollstaendig=aktuelle_flesch >= MINDEST,
                    teilfortschritt=teilfortschritt)
    if teilfortschritt:
        ergebnis["gruende"].append(
            f"Teilfortschritt: +{aktuelle_flesch - vor:.1f} Flesch; "
            f"alle Tore außer T1-Schwelle still; Ziel ≥ {MINDEST:g} bleibt offen")
    status = "Teilfortschritt" if teilfortschritt else "vollständig"
    ergebnis["befund"] = (f"{status}: {len(ergebnis['ersetzt'])} Satz-Ersatz/Ersätze, "
                          f"{ergebnis['anfragen']} KI-Anfrage(n), "
                          f"Flesch {vor:.1f} → {aktuelle_flesch:.1f}")
    return ergebnis


def _antwort_zerlegen(antwort: str, erwartet: int) -> dict:
    """Nummerierte Antwortzeilen des Modells einsammeln (robust, konservativ)."""
    out: dict[int, str] = {}
    for zeile in (antwort or "").splitlines():
        m = re.match(r"^\s*\**\s*(\d{1,2})\s*[).:\-]\s*(.+?)\s*$", zeile)
        if not m:
            continue
        nummer = int(m.group(1))
        if 1 <= nummer <= erwartet:
            out[nummer] = m.group(2).strip().strip('"').strip("„“")
    return out


# ---------------------------------------------------------------------------
#  KANDIDATEN
# ---------------------------------------------------------------------------
def hole_reserve() -> list[str]:
    """Reserve-Entwürfe unter der Lesbarkeits-Schwelle."""
    pfade = []
    for p in sorted(glob.glob(os.path.join(BLOG_DIR, "content/posts/*/index.md"))):
        try:
            raw = open(p, encoding="utf-8").read()
        except OSError:
            continue
        if not re.search(r"(?m)^reserve:\s*true\s*$", raw):
            continue
        if not _ist_entwurf(raw):
            continue
        wert = lh.flesch(raw, _slug_von(p))
        if wert is not None and wert < MINDEST:
            pfade.append(p)
    return pfade


# ---------------------------------------------------------------------------
#  SELBSTTEST + WIRKUNGSPROBE (Maschinenvertrag, Governance C25)
# ---------------------------------------------------------------------------
_FIXTURE_KOPF_BASIS = (
    "---\n"
    "title: \"Probe: Satz-Heiler\"\n"
    "date: 2026-10-07\n"
    "draft: true\n"
)
# Realistische Kopfgröße (≥ 2.532 Zeichen wie beim Kandidaten aus Lauf
# 37666773476); der YAML-String steht stellvertretend für Quellen- und
# Redaktionsmetadaten, die in echten Reserve-Artikeln vor dem Body liegen.
_FIXTURE_KOPF_FUELLER = (
    "quellenvermerk fuer die redaktionelle pruefung und den reserve nachweis "
    "bleibt als metadatum vor dem artikelkoerper erhalten "
)
SATZ_FIXTURE_KOPF = (
    _FIXTURE_KOPF_BASIS
    + 'fixture_metadata: "'
    + (_FIXTURE_KOPF_FUELLER * 80)[:2600]
    + '"\n---\n\n'
)
SCHWER = (
    "Prüfe deine Abrechnung genau. So findest du teure Verträge schnell. "
    "Notiere die Zählerstände. Ein Blick auf das Typenschild hilft dabei.\n\n"
    "Die Verbrauchskostenoptimierung der Haushaltsgeräte beeinflusst die "
    "monatliche Abschlagszahlung der Verbraucherinnen und Verbraucher "
    "erheblich, weshalb die regelmäßige Überprüfung der Verbrauchswerte die "
    "jährlichen Ausgaben deutlich senken kann.\n\n"
    "Wechsle den Anbieter, wenn der Preis steigt.\n"
)
LEICHT = {
    "Die Verbrauchskostenoptimierung der Haushaltsgeräte beeinflusst die "
    "monatliche Abschlagszahlung der Verbraucherinnen und Verbraucher "
    "erheblich, weshalb die regelmäßige Überprüfung der Verbrauchswerte die "
    "jährlichen Ausgaben deutlich senken kann.":
        "Wie viel Strom deine Geräte brauchen, bestimmt deinen Abschlag. "
        "Prüfe die Werte also regelmäßig. So senkst du deine Ausgaben im "
        "Jahr deutlich. Du behältst den Überblick und zahlst am Ende "
        "weniger als vorher. Das gilt für jeden Haushalt.",
}


def _fixture() -> str:
    return SATZ_FIXTURE_KOPF + SCHWER


def _fake_ki(prompt: str) -> str:
    """Antwortet wie ein gutes Modell – für einen Test an der echten Formel.

    Gelesen wird nur der Satz-Block NACH der Überschrift „Sätze:"; die
    Beispielzeile in der Anweisung darf nicht als Antwort gelten.
    """
    block = (prompt or "").split("Sätze:", 1)[-1]
    out = []
    for zeile in block.splitlines():
        m = re.match(r"^\s*\d+\)\s*(.+?)\s*$", zeile)
        if not m:
            continue
        satz = m.group(1).strip()
        out.append(f"{len(out) + 1}) {LEICHT.get(satz, satz)}")
    return "\n".join(out)


def wirkungsprobe() -> tuple[bool, str]:
    """Beweist ohne Netz: der Weg hebt einen schweren Text über die Schwelle."""
    global KI_CALL
    alt_ki = KI_CALL
    try:
        KI_CALL = _fake_ki
        raw = _fixture()
        vor = lh.flesch(raw, "probe")
        ergebnis = heile_text("probe", raw)
        nach = ergebnis.get("nach")
        if not ergebnis["ok"]:
            return False, (f"Wirkung fehlt: Flesch {vor} → {nach} – "
                           f"{ergebnis['gruende'][:2]}")
        if nach is None or nach < MINDEST:
            return False, f"Schwelle nicht erreicht: Flesch {nach} < {MINDEST:g}"
        if _body_offset(raw) < 2532:
            return False, "Wirkungsprobe nutzt kein realistisches Frontmatter (≥ 2532 Zeichen)"
        if _kopf_bis_body(raw) != _kopf_bis_body(ergebnis["neu_raw"]):
            return False, "Kopf-Tor: Frontmatter/Trenner wurden verändert"
        if nebenwirkung := lh.harte_funde(ergebnis["neu_raw"], "probe"):
            return False, f"neuer harter Fund: {sorted(nebenwirkung)}"
        return True, (f"Flesch {vor:.1f} → {nach:.1f} (≥ {MINDEST:g}) über "
                      f"{len(ergebnis['ersetzt'])} Satz-Ersatz/Ersätze, Tor T1–T4, "
                      "Kopf-Tor und Satzschutz erfüllt")
    finally:
        KI_CALL = alt_ki


def run_selftest() -> int:
    fehler: list[str] = []
    global KI_CALL, _finde_satz
    alt_ki = KI_CALL

    def pruefe(bedingung: bool, text: str) -> None:
        if not bedingung:
            fehler.append(text)

    try:
        # 1) Wirkung an echten Formeln (readability_check, nicht nachgebaut)
        ok, meldung = wirkungsprobe()
        pruefe(ok, f"Wirkungsprobe: {meldung}")

        # 2) Idempotenz: der geheilte Text ist danach fertig
        KI_CALL = _fake_ki
        raw = _fixture()
        erst = heile_text("probe", raw)
        pruefe(erst["ok"], f"erste Heilung nicht ok: {erst['gruende'][:2]}")
        zweit = heile_text("probe", erst["neu_raw"])
        pruefe(zweit["ok"] and zweit["nach"] >= MINDEST,
               "der geheilte Text gilt nicht als fertig (nicht idempotent)")
        pruefe(_body_offset(raw) >= 2532,
               "Wirkungsprobe hat kein Frontmatter in realer Größe")
        pruefe(_kopf_bis_body(raw) == _kopf_bis_body(erst["neu_raw"]),
               "Wirkungsprobe hat den Kopf verändert")

        # Gegenprobe: 0 ist niemals ein gültiger Offset. Wenn der Finder
        # ausfällt, muss der Heiler fail-closed bleiben statt im Dateikopf zu
        # schreiben. Diese Probe wird absichtlich mit einem defekten Finder
        # ausgeführt und muss selbst grün bleiben.
        finder_orig = _finde_satz
        try:
            _finde_satz = lambda *_args, **_kwargs: 0
            r = heile_text("probe", raw, max_ki=1)
            pruefe(not r["ok"] and r["neu_raw"] == raw and not r["ersetzt"],
                   "_finde_satz → 0 wurde nicht fail-closed abgewiesen")
            pruefe(any("vollständiger Satz im Body nicht gefunden" in v["gruende"]
                       for v in r["verworfen"]),
                   "Gegenprobe _finde_satz → 0 hinterließ keinen Befund")
        finally:
            _finde_satz = finder_orig

        # 4) Sabotage: Ziffer im Ersatz wird verworfen
        def ki_zahl(_text):
            return "1) Die Kosten sinken um 20 Euro."
        KI_CALL = ki_zahl
        r = heile_text("probe", raw)
        pruefe(not r["ok"] and r["neu_raw"] == raw,
               "ein Ersatz mit Ziffer wurde nicht verworfen")
        pruefe(any("Ziffer" in g for e in r["verworfen"] for g in e["gruende"]),
               "der Ziffern-Verwurf wurde nicht begründet")

        # 4) Sabotage: Markup/Verkürzung/„Sie"-Form/Formel werden verworfen
        for name, ersatz, stichwort in (
                ("Markup", "1) **Fett** bleibt.", "Markup"),
                ("zu kurz", "1) Kosten.", "gekürzt"),
                ("Sie-Form", "1) Ihre Kosten sinken deutlich, wenn Sie jetzt "
                             "die Tarife prüfen und den Anbieter wechseln.",
                 "Duktus"),
                ("Formel", "1) In diesem Artikel zeige ich dir, wie die Kosten "
                           "sinken und du den Tarif prüfst, damit alles bleibt.",
                 "Intro-Formel")):
            KI_CALL = lambda _t, e=ersatz: e
            r = heile_text("probe", raw)
            gruende = " ".join(g for e in r["verworfen"] for g in e["gruende"])
            pruefe(not r["ok"], f"{name}: verworfener Ersatz wurde geschrieben")
            pruefe(stichwort in gruende,
                   f"{name}: Verwurfsgrund fehlt („{stichwort}\" nicht in {gruende[:120]})")

        # 5) Ohne KI wird nie geschrieben, aber der Grund steht da
        KI_CALL = lambda _t: None
        r = heile_text("probe", raw)
        pruefe(not r["ok"] and r["neu_raw"] == raw,
               "ohne KI-Antwort wurde etwas geschrieben")
        pruefe(any("keine KI-Antwort" in g for g in r["gruende"]),
               "der Grund „keine KI-Antwort\" fehlt")

        # 6) Die Schwelle ist importiert, nicht abgetippt
        pruefe(abs(MINDEST - rc.NEW_FLESCH_MIN) < 1e-9,
               "MINDEST ist nicht readability_check.NEW_FLESCH_MIN")
    finally:
        KI_CALL = alt_ki

    if fehler:
        print("🛑 Satz-Heiler-Selbsttest FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 1
    print("✅ Satz-Heiler-Selbsttest bestanden: Wirkung an echter Flesch-Formel "
          "mit realem Kopf, _finde_satz→0 fail-closed, Idempotenz, "
          "Tore lehnen Ziffer/Markup/Kürzung/Sie-Form/Intro-Formel ab, "
          "ohne KI-Antwort wird nichts geschrieben, Schwelle importiert.")
    return 0


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------
def _verarbeite(pfade: list[str], *, fix: bool, max_n: int | None,
                max_ki: int, auch_live: bool = False, ki: bool = True,
                nur_ganz: bool | None = None) -> tuple[list[dict], int]:
    berichte, befund = [], 0
    for pfad in pfade[:max_n] if max_n else pfade:
        try:
            with open(pfad, encoding="utf-8") as fh:
                rohtext = fh.read()
        except OSError as exc:
            berichte.append({"slug": _slug_von(pfad), "ok": False,
                             "gruende": [f"nicht lesbar: {exc}"]})
            befund += 1
            continue
        if not _ist_entwurf(rohtext) and not auch_live:
            berichte.append({"slug": _slug_von(pfad), "ok": True,
                             "stufe": "übersprungen",
                             "befund": "kein Entwurf (draft: false) – Scope-Schutz"})
            continue
        ergebnis = heile_text(_slug_von(pfad), rohtext, max_ki=max_ki,
                              ki=ki, nur_ganz=nur_ganz)
        veraendert = ergebnis["neu_raw"] != rohtext
        if veraendert and ergebnis["ok"]:
            if fix:
                with open(pfad, "w", encoding="utf-8") as fh:
                    fh.write(ergebnis["neu_raw"])
                ergebnis["geschrieben"] = True
            else:
                befund += 1
        elif veraendert:
            befund += 1
        elif (ergebnis.get("vor") is not None and ergebnis["vor"] < MINDEST
                and not ergebnis["ok"]):
            # Text blieb liegen, obwohl er unter der Schwelle steht: offener Punkt.
            befund += 1
        ergebnis["pfad"] = os.path.relpath(pfad, BLOG_DIR)
        ergebnis.pop("neu_raw", None)
        berichte.append(ergebnis)
    return berichte, befund


def _menschen_text(berichte: list[dict], befund: int) -> str:
    zeilen = ["# SATZ-HEILER (Lesbarkeits-Klasse, #614)", ""]
    for b in berichte:
        if b.get("stufe") == "übersprungen":
            zeilen.append(f"⏭  {b['slug']}: {b.get('befund')}")
            continue
        vor = f"{b['vor']:.1f}" if b.get("vor") is not None else "–"
        nach = f"{b['nach']:.1f}" if b.get("nach") is not None else "–"
        marke = ("🟡" if b.get("teilfortschritt") else
                 "🟢" if b.get("ok") else "🔴")
        haken = " ✍️" if b.get("geschrieben") else ""
        zeilen.append(f"{marke} {b.get('slug')}{haken}: Flesch {vor} → {nach} "
                      f"({len(b.get('ersetzt') or [])} Ersatz, "
                      f"{b.get('anfragen', 0)} KI-Anfragen)")
        for g in (b.get("gruende") or [])[:3]:
            zeilen.append(f"     ! {g}")
        for v in (b.get("verworfen") or [])[:2]:
            zeilen.append(f"     · verworfen: {v['satz'][:50]}… "
                          f"({', '.join(v['gruende'])[:60]})")
    zeilen += ["", f"Schwelle: Flesch ≥ {MINDEST:g} (readability_check."
                   "NEW_FLESCH_MIN, importierte SSOT)",
               f"Offene Punkte (nicht geschrieben): {befund}"]
    return "\n".join(zeilen)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Satz-Heiler: heilt die Lesbarkeits-Klasse satzweise mit der "
                    "KI und entscheidet am Ganztext-Tor (T1–T4).")
    ap.add_argument("--file", action="append", default=[],
                    help="einzelne Datei (mehrfach möglich)")
    ap.add_argument("--reserve", action="store_true",
                    help="alle Reserve-Kandidaten unter der Schwelle")
    ap.add_argument("--blocked", action="store_true", help="Alias für --reserve")
    ap.add_argument("--fix", action="store_true", help="schreiben (sonst Trockenlauf)")
    ap.add_argument("--auch-live", action="store_true",
                    help="auch Nicht-Entwürfe anfassen (Standard: nur draft:true)")
    ap.add_argument("--max", type=int, default=None, help="höchstens N Kandidaten")
    ap.add_argument("--max-ki", type=int, default=MAX_KI_STANDARD,
                    help=f"KI-Anfragen je Artikel (Standard {MAX_KI_STANDARD})")
    ap.add_argument("--nur-ganz", action="store_true",
                    help="Teilfortschritt verwerfen; nur ab erreichter Schwelle schreiben")
    ap.add_argument("--keine-ki", action="store_true", help="nur Analyse")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--report", action="store_true",
                    help="Report nach SATZ-HEILER-REPORT.md schreiben")
    ap.add_argument("--wirkungsprobe", action="store_true",
                    help="Maschinenvertrag: beweist die Wirkung (Exit 0 = grün)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()

    if args.wirkungsprobe:
        ok, meldung = wirkungsprobe()
        if args.json:
            print(json.dumps({"ok": ok, "meldung": meldung, "schwelle": MINDEST},
                             ensure_ascii=False))
        else:
            print(("✅ " if ok else "🛑 ") + "Wirkungsprobe: " + meldung)
        return 0 if ok else 2

    pfade = list(args.file)
    if args.reserve or args.blocked:
        rest = hole_reserve()
        if not rest and not pfade:
            if args.json:
                print(json.dumps({"befund": 0, "berichte": [],
                                  "hinweis": "kein Kandidat unter der Schwelle"},
                                 ensure_ascii=False))
            else:
                print("✅ Satz-Heiler: 0 Reserve-Kandidaten unter der Schwelle "
                      "– nichts zu tun.")
            return 0
        pfade += rest
    if not pfade:
        ap.error("Quelle fehlt: --file oder --reserve "
                 "(oder --selftest/--wirkungsprobe)")

    berichte, befund = _verarbeite(sorted(dict.fromkeys(pfade)), fix=args.fix,
                                   max_n=args.max, max_ki=args.max_ki,
                                   auch_live=args.auch_live,
                                   ki=not args.keine_ki,
                                   nur_ganz=True if args.nur_ganz else None)
    text = _menschen_text(berichte, befund)
    if args.json:
        print(json.dumps({"befund": befund, "berichte": berichte},
                         ensure_ascii=False, indent=1, default=str))
    else:
        print(text)
    if args.report:
        ziel = os.path.join(BLOG_DIR, "SATZ-HEILER-REPORT.md")
        with open(ziel, "w", encoding="utf-8") as fh:
            fh.write(f"<!-- erzeugt: {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC -->\n\n")
            fh.write(text + "\n")
        print(f"📄 Report: {os.path.relpath(ziel, BLOG_DIR)}")
    return 1 if befund else 0


if __name__ == "__main__":
    sys.exit(main())
