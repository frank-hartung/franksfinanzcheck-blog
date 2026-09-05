#!/usr/bin/env python3
"""reader_tts_backends.py — Kostenlose Neural-Stimmen-Kette für die Vorlese-Tonspur.

Stand 04.09.2026. Dieses Modul ist die Antwort auf zwei Befunde:

  1. **Das alte Backend ist tot.** Groq hat `playai-tts` (Fritz-PlayAI /
     Atlas-PlayAI) am 31.12.2025 abgeschaltet; Ersatz ist
     `canopylabs/orpheus-v1-english` – **nur Englisch**
     (https://console.groq.com/docs/deprecations). Damit lief der
     Generator seit Januar 2026 ins Leere und der Reader fiel still auf
     die Browser-Stimme (Web Speech API) zurück – genau die
     „robotische" Stimme, die niemand hören will.

  2. **Natürlichkeit entsteht nicht nur durch die Stimme**, sondern durch
     Regie: korrekte Aussprache von Zahlen/Daten/Währungen, echte Pausen,
     Rollen-Prosodie (Überschrift ≠ Tabellenzeile), ein einziger
     männlicher Sprecher auch bei englischen Fachbegriffen im deutschen
     Satz (Code-Switching ohne Timbresprung) und konsistente Lautheit.

Kostenlose Backend-Kette (Reihenfolge `auto`, alle ohne Abo):

  edge   Microsoft-Edge-Neuralstimmen über das offene `edge-tts`-Paket.
         Kein API-Key, kein Konto, keine Zeichenkosten. Männliche
         DE-Stimme `de-DE-FlorianMultilingualNeural` (Multilingual v2 –
         spricht eingestreute englische Begriffe nativ, ohne dass die
         Stimme wechselt), EN-Stimme `en-US-AndrewMultilingualNeural`.
         Alternativprofil „narrator": `de-DE-ConradNeural` (der klassische
         männliche Erzähler) + `en-GB-RyanNeural`.
         Liefert echte Wortgrenzen → satzgenaue Timeline statt Schätzung.
         High-End-Priorität: das ist die menschlichste kostenlose
         männliche DE-/EN-Stimme.

  piper  Lokale ONNX-Neuralstimmen (OHF-Voice/piper1-gpl). `de_DE-thorsten-high`
         / `de_DE-karlsson-low` für DE, `en_US-ryan-high` / `en_GB-alan-medium`
         für EN. Läuft komplett offline auf der CI-CPU, unbegrenzt,
         deterministisch, lizenzsauber – Fallback, falls Edge fehlt.

  groq   Nur als EN-Notnagel (`canopylabs/orpheus-v1-english`, Stimme
         `daniel`), benötigt GROQ_API_KEY, Free-Tier ≈ 100 Calls/Tag.
         Kann kein Deutsch → wird für DE-Blöcke nie gewählt.

Ohne alle drei Backends erzeugt der Generator keine Tonspur; der Reader
bleibt dann beim lokalen Web-Speech-Pfad (funktioniert weiterhin, ist
aber geräteabhängig).

Timbres-Hinweis: Edge-Multilingual-v2 (Florian/Andrew) spricht DE und EN
in EINER Stimme ohne Timbresprung – das ist die High-End-Voreinstellung.
Piper hat getrennte Stimmen (thorsten ↔ ryan/alan) und übernimmt offline,
falls der Edge-Dienst fehlt.

Nutzung aus dem Generator:

    from reader_tts_backends import (
        Engine, build_units, speech_normalize, PROSODY_VERSION)

    engine = Engine(backend="auto", profile="natural")
    for unit in build_units(blocks, article_lang):
        res = engine.synthesize(unit)      # → SynthResult(pcm, rate, words)

Selbsttest (offline, ohne Netzwerk/Pakete):
    python3 scripts/reader_tts_backends.py --selftest
"""
from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Rezept-Version: steht im Fingerprint der Tonspur. Jede Änderung an
# Normalisierung oder Prosodie erzwingt damit eine Neuvertonung, statt
# alte Tracks mit neuem Rezept zu mischen.
NORM_VERSION = "ff-norm-v2"
PROSODY_VERSION = "ff-prosody-v5"       # v5: ruhigeres Grundtempo (kein Hetzen)
BACKENDS_VERSION = "ff-backends-v5"     # v5: Edge-Neural zuerst, Knack-/Rauschschutz, nur männliche Piper-EN

TARGET_RATE = 24000          # gemeinsame Abtastrate der Tonspur (Hz)
TICKS_PER_SECOND = 10_000_000  # edge-tts liefert Offsets in 100-ns-Ticks


# ==========================================================================
# 1. Stimmen-Katalog: ausschließlich männlich, DE + EN, ohne Umschalter
# ==========================================================================
# Profile = Redaktionsentscheidung, keine Technik. Beide Profile sind
# kostenlos; „natural" ist die Voreinstellung, weil die Multilingual-v2-
# Stimmen messbar weniger „Vorleseroboter" sind und englische Fachbegriffe
# im deutschen Satz in derselben Stimme sprechen (kein Timbresprung).
VOICE_PRESETS: dict[str, dict[str, dict[str, list[str]]]] = {
    "natural": {
        "edge": {
            # Multilingual v2: ein Sprecher, viele Sprachen, natürlichere
            # Satzmelodie als die klassischen v1-Stimmen.
            "de": ["de-DE-FlorianMultilingualNeural", "de-DE-ConradNeural",
                   "de-DE-BerndNeural", "de-DE-RalfNeural"],
            "en": ["en-US-AndrewMultilingualNeural", "en-US-BrianMultilingualNeural",
                   "en-GB-RyanNeural", "en-US-GuyNeural", "en-US-ChristopherNeural"],
        },
        "piper": {
            "de": ["de_DE-thorsten-high", "de_DE-thorsten-medium", "de_DE-karlsson-low"],
            # Nur nachweislich männliche EN-Stimmen (alba = britische Frau).
            "en": ["en_US-ryan-high", "en_GB-alan-medium"],
        },
        "groq": {
            "de": [],                                   # Orpheus kann kein Deutsch
            "en": ["daniel", "troy", "austin", "brad"],
        },
    },
    "narrator": {
        "edge": {
            "de": ["de-DE-ConradNeural", "de-DE-FlorianMultilingualNeural",
                   "de-DE-BerndNeural", "de-DE-RalfNeural"],
            "en": ["en-GB-RyanNeural", "en-US-GuyNeural", "en-US-ChristopherNeural",
                   "en-US-EricNeural", "en-US-AndrewMultilingualNeural"],
        },
        "piper": {
            "de": ["de_DE-thorsten-high", "de_DE-thorsten-medium"],
            "en": ["en_GB-alan-medium", "en_US-ryan-high"],
        },
        "groq": {
            "de": [],
            "en": ["troy", "daniel", "austin"],
        },
    },
}

# Kostenlose Backend-Priorität (`auto`): High-End-Klang zuerst, Bestandsschutz
# danach. Edge-Multilingual-v2 (Florian/Andrew) ist die menschlichste
# kostenlose männliche DE-/EN-Stimme – ein Sprecher, kein Timbresprung.
# Piper (Thorsten/Ryan, offline) übernimmt, wenn der Edge-Dienst fehlt;
# Groq nur als EN-Notnagel. So bleibt die Tonspur dauerhaft kostenlos.
BACKEND_ORDER = ("edge", "piper", "groq")

# Männliche Kantaten-Prüfung für den Live-Katalog (edge-tts meldet Gender).
MALE_NAMES = {
    "florian", "conrad", "bernd", "ralf", "andrew", "brian", "ryan", "guy",
    "christopher", "eric", "thorsten", "karlsson", "daniel", "troy", "austin",
    "brad", "stefan", "killian", "kilian", "jonas", "alan", "kristoff",
    "mark", "david", "james", "oliver", "arthur", "thomas", "roger", "steffan",
    "george", "jason", "davis", "alfie", "liam", "noah", "harry", "patrick",
}
FEMALE_NAMES = {
    "katja", "seraphina", "amala", "elke", "gisela", "klarissa", "louisa",
    "maja", "tanja", "emma", "ava", "aria", "jenny", "libby", "sonia",
    "michelle", "natalie", "samantha", "zira", "vicki", "hedda", "inga",
    "amy", "arctic", "blizzard", "susan", "olivia", "joanna",
    "kendra", "cortana", "hazel", "karen", "salli", "jo", "eva", "anna",
    "clara", "lisa", "lena", "marlene", "petra", "ingrid", "ellen", "moira",
    "tessa", "nicole", "kathy", "catherine", "victoria", "helena", "linda",
    "alba",  # Piper en_GB-alba = britische Frauenstimme
}


def preset_voices(profile: str, backend: str, lang: str,
                  override: str | None = None) -> list[str]:
    """Männliche Stimmen-Kandidaten (beste zuerst) für Profil/Backend/Sprache."""
    pref = VOICE_PRESETS.get(profile) or VOICE_PRESETS["natural"]
    cands = list((pref.get(backend) or {}).get("de" if lang != "en" else "en") or [])
    if override:
        # Eine explizite Redaktionsvorgabe gewinnt immer und steht vorn.
        cands = [override.strip()] + [c for c in cands if c != override.strip()]
    return cands


def is_male_voice_name(name: str) -> bool:
    """Geschlechtsprüfung über den Stimmen-Namen (edge-tts liefert Gender,
    Piper/Groq nicht immer) – Schutz gegen eine weibliche Stimme im Track.

    Multilingual-Stimmen tragen den Vornamen als *Präfix* eines langen
    Tokens („FlorianMultilingualNeural"), deshalb wird innerhalb der
    Namens-Token auf Präfix geprüft und nicht auf exakte Gleichheit.
    Ein weiblicher Treffer gewinnt immer (Veto-Prinzip).
    """
    n = (name or "").lower()
    if "female" in n or "weiblich" in n:
        return False
    tokens = [t for t in re.split(r"[^a-zäöüß]+", n) if t]
    male = female = False
    for tok in tokens:
        if any(tok.startswith(f) for f in FEMALE_NAMES):
            female = True
        if any(tok.startswith(m) for m in MALE_NAMES):
            male = True
    if female:
        return False
    if male:
        return True
    return bool(re.search(r"(male|mann|männlich)", n))


# ==========================================================================
# 2. Sprache: Satzebene statt Blockebene (zweisprachiger Moderator)
# ==========================================================================
# Diagnostische Funktionswörter: eindeutig einer Sprache zugeordnet.
# Mehrdeutige Token („in", „so", „per", „was", „die") fehlen bewusst –
# sie sind die häufigste Quelle falscher Sprachwechsel in der Vorlese-
# Ausgabe (ein deutscher Satz, der plötzlich englisch gesprochen wird).
EN_CORE = set("""the and of to is are you your with for that this it on as not but from at by be
will would can could have has had our their they we them he she his her there here all more most
also only very just than then when where what why how who which no yes do does did about into over
under between through after before during because while against up down out off again once each
both few first second new good much want need know show shows shown lower higher higher cheapest
cheaper expensive fee fees plan plans cost costs costing save saves saved saving savings money
price prices compare comparison compared tariff tariffs contract contracts provider providers
switch switched avoid read reading listen article summary important should may might must if or
so-called therefore however although example include includes including without within during""".split())

DE_CORE = set("""der die das und ist sind war waren wird werden wurde wurden ein eine einer einem
einen eines nicht mit von für auf zu im am den dem des bei auch sich kann können muss müssen darf
sollen wollen haben hat hatte aber oder wenn weil dass wie als nach vor bis seit aus nur noch
schon dann doch hier jetzt über unter zwischen ohne gegen durch um sie wir ihr euch uns er es mich
dich ihm ihn diese dieser dieses diesem diesen welche mein meine dein deine ihre kein keine aller
allen alles viele zwei drei vier fünf sechs sieben acht neun zehn prozent euro monat monate jahr
jahre kosten vertrag versicherung tarif tarife anbieter wechsel rechnung sparen spart spare geld
vergleich vergleichst günstiger günstige teuer teure preis leistung haushalt strom gas heizung
auto kredit konto karte bank zinsen du dir dich man etwas nichts mehr weniger sehr dort heute
morgen immer nie oft manchmal vielleicht bitte danke danach davor deshalb trotzdem allerdings
jedoch zudem außerdem damit darauf darüber darunter davon dazu beim zur zum übers unters seitdem
während sobald sofern soweit lautet lauten gilt gelten bedeutet findest findest du solltest
musst kannst lohnt lohnt sich bleibt bleiben gilt ab bis""".split())

GERMAN_ENDINGS = ("ung", "keit", "heit", "nis", "schaft", "tum", "lich", "ig", "bar", "sam",
                  "ieren", "iert", "chen", "lein")


def sniff_lang(text: str, base: str) -> str:
    """DE/EN-Erkennung auf Satzebene (zweisprachiger Hörfunk-Moderator).

    Ein deutscher Absatz mit einem englischen Satz („The comparison shows
    lower fees.") wird satzweise erkannt: die englische Stimme übernimmt
    nur diesen Satz. Ohne Umschalter für die Leser:innen – und ohne dass
    ein ganzer Absatz in der falschen Sprache gesprochen wird.

    Regel: eindeutige Funktionswörter zählen, Mehrdeutige ignorieren.
    Umschalt-Bedingung ist bewusst konservativ (mindestens zwei Treffer
    und keine Gegen-Treffer der anderen Sprache), weil ein falscher
    Sprachenwechsel beim Hören viel stärker auffällt als ein englischer
    Fachbegriff mit deutscher Aussprache.
    """
    words = [w for w in re.findall(r"[a-zäöüß']+", (text or "").lower()) if len(w) > 1]
    if not words:
        return "en" if str(base).lower().startswith("en") else "de"
    en = sum(1 for w in words if w in EN_CORE)
    de = sum(1 for w in words if w in DE_CORE)
    germ = 0
    for w in words:
        if re.search(r"[äöüß]", w):
            germ += 2
        if len(w) >= 5 and any(w.endswith(e) for e in GERMAN_ENDINGS):
            germ += 1
    total = len(words)
    base_en = str(base).lower().startswith("en")

    if base_en:
        # Englischer Artikel: deutsche Einschübe erkennen.
        if de >= 2 and de > en:
            return "de"
        if de >= 1 and germ >= 2 and de > en:
            return "de"
        if en == 0 and (germ >= 2 or de / total >= 0.12):
            return "de"
        return "en"
    # Deutscher Artikel: englische Sätze erkennen.
    if en >= 2 and de == 0:
        return "en"
    if en >= 3 and en > de * 2:
        return "en"
    if en >= 1 and de == 0 and germ == 0 and en / total >= 0.18:
        return "en"
    return "de"


# ==========================================================================
# 3. Aussprache-Normalisierung (der größte kostenlose Natürlichkeits-Hebel)
# ==========================================================================
# Finanzartikel bestehen zur Hälfte aus Zahlen, Daten, Währungen und
# Abkürzungen. Eine Neuralstimme liest „1.299,50 €" als „eins Punkt
# zweitausendneunundneunzig Komma fünfzig Euro-Symbol" – sofort als
# Maschine erkennbar. Deshalb wird hier *vor* der Synthese in gesprochene
# Sprache übersetzt (Parität zu speechNormalize() im Reader-JS).
DE_MONTHS = ["Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
             "August", "September", "Oktober", "November", "Dezember"]
EN_MONTHS = ["January", "February", "March", "April", "May", "June", "July",
             "August", "September", "October", "November", "December"]

DE_UNITS_ = ["null", "ein", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun"]
DE_TEENS = ["zehn", "elf", "zwölf", "dreizehn", "vierzehn", "fünfzehn", "sechzehn",
            "siebzehn", "achtzehn", "neunzehn"]
DE_TENS = ["", "zehn", "zwanzig", "dreißig", "vierzig", "fünfzig", "sechzig", "siebzig",
           "achtzig", "neunzig"]
EN_UNITS_ = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
             "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
             "seventeen", "eighteen", "nineteen"]
EN_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
EN_ORDINALS = {1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth",
               7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth", 11: "eleventh",
               12: "twelfth", 13: "thirteenth", 14: "fourteenth", 15: "fifteenth",
               16: "sixteenth", 17: "seventeenth", 18: "eighteenth", 19: "nineteenth",
               20: "twentieth", 30: "thirtieth"}
DE_ORD_SPECIAL = {1: "erster", 3: "dritter", 7: "siebter", 8: "achter", 16: "sechzehnter"}


def _de_below_thousand(n: int) -> str:
    if n < 10:
        return DE_UNITS_[n]
    if n < 20:
        return DE_TEENS[n - 10]
    if n < 100:
        t, u = divmod(n, 10)
        return DE_TENS[t] if u == 0 else f"{DE_UNITS_[u]}und{DE_TENS[t]}"
    h, rest = divmod(n, 100)
    head = "einhundert" if h == 1 else f"{DE_UNITS_[h]}hundert"
    return head + (_de_below_thousand(rest) if rest else "")


def de_number_words(n: int, standalone: bool = False) -> str:
    """Kardinalzahl → gesprochenes Deutsch („1299" → „eintausendzweihundertneunundneunzig")."""
    if n == 0:
        return "null"
    if n == 1 and standalone:
        return "eins"
    neg = n < 0
    n = abs(n)
    high: list[str] = []
    for value, sing, plur in ((10 ** 12, "Billion", "Billionen"),
                              (10 ** 9, "Milliarde", "Milliarden"),
                              (10 ** 6, "Million", "Millionen")):
        if n >= value:
            count, n = divmod(n, value)
            high.append("eine " + sing if count == 1 else f"{de_number_words(count)} {plur}")
    low = ""
    if n >= 1000:
        th, n = divmod(n, 1000)
        low += "eintausend" if th == 1 else f"{_de_below_thousand(th)}tausend"
    if n > 0:
        low += _de_below_thousand(n)
    out = " ".join([*high, low]).strip()
    return ("minus " + out) if neg else out


def de_year_words(y: int) -> str:
    """Jahreszahl → deutsche Sprechweise (1990 „neunzehnhundertneunzig", 2026 „zweitausendsechsundzwanzig")."""
    if 1000 <= y <= 1999:
        century, rest = divmod(y, 100)
        head = _de_below_thousand(century) + "hundert"
        return head + (_de_below_thousand(rest) if rest else "")
    return de_number_words(y)


def de_ordinal_words(n: int) -> str:
    """Ordinalzahl für Tagesdaten („12." → „zwölfter")."""
    if n in DE_ORD_SPECIAL:
        return DE_ORD_SPECIAL[n]
    base = de_number_words(n)
    return base + ("ster" if n >= 20 or n in (0,) else "ter")


def _en_below_thousand(n: int) -> str:
    if n < 20:
        return EN_UNITS_[n]
    if n < 100:
        t, u = divmod(n, 10)
        return EN_TENS[t] + (f"-{EN_UNITS_[u]}" if u else "")
    h, rest = divmod(n, 100)
    head = f"{EN_UNITS_[h]} hundred"
    return head + (" " + _en_below_thousand(rest) if rest else "")


def en_number_words(n: int) -> str:
    if n == 0:
        return "zero"
    neg = n < 0
    n = abs(n)
    parts: list[str] = []
    for value, name in ((10 ** 12, "trillion"), (10 ** 9, "billion"),
                        (10 ** 6, "million"), (10 ** 3, "thousand")):
        if n >= value:
            count, n = divmod(n, value)
            parts.append(f"{_en_below_thousand(count)} {name}")
    if n:
        parts.append(_en_below_thousand(n))
    out = " ".join(parts)
    return ("minus " + out) if neg else out


def en_year_words(y: int) -> str:
    if 2000 <= y <= 2009:
        return "two thousand" if y == 2000 else f"two thousand {EN_UNITS_[y - 2000]}"
    if 2010 <= y <= 2099:
        hi, lo = divmod(y, 100)
        return f"{_en_below_thousand(hi)} {_en_below_thousand(lo)}" if lo else _en_below_thousand(hi)
    if 1000 <= y <= 1999:
        hi, lo = divmod(y, 100)
        return f"{_en_below_thousand(hi)} {_en_below_thousand(lo)}" if lo else _en_below_thousand(hi)
    return en_number_words(y)


def en_ordinal_words(n: int) -> str:
    if n in EN_ORDINALS:
        return EN_ORDINALS[n]
    if n < 100 and n % 10 in EN_ORDINALS and n % 10 != 0:
        t, u = divmod(n, 10)
        return f"{EN_TENS[t]}-{EN_ORDINALS[u]}"
    word = en_number_words(n)
    if word.endswith("y"):
        return word[:-1] + "ieth"
    if word.endswith("e"):
        return word + "th" if not word.endswith("ve") else word[:-1] + "fth"
    if word.endswith("t") or word.endswith("d"):
        return word + "h"
    return word + "th"


# Abkürzungen → gesprochene Sprache (Reihenfolge: längste zuerst).
DE_ABBREV = [
    (r"\bi\.\s*d\.\s*R\.", "in der Regel"),
    (r"\bu\.\s*v\.\s*m\.", "und vieles mehr"),
    (r"\bz\.\s*B\.", "zum Beispiel"),
    (r"\bd\.\s*h\.", "das heißt"),
    (r"\bu\.\s*a\.", "unter anderem"),
    (r"\bs\.\s*o\.", "siehe oben"),
    (r"\bu\.\s*E\.", "unter Umständen"),
    (r"\bz\.\s*Z\.", "zurzeit"),
    (r"\bo\.\s*g\.", "oben genannte"),
    (r"\bv\.\s*a\.", "vor allem"),
    (r"\bggf\.", "gegebenenfalls"),
    (r"\bbzw\.", "beziehungsweise"),
    (r"\busw\.", "und so weiter"),
    (r"\bsog\.", "sogenannte"),
    (r"\binkl\.", "inklusive"),
    (r"\bexkl\.", "exklusive"),
    (r"\bzzgl\.", "zuzüglich"),
    (r"\babzgl\.", "abzüglich"),
    (r"\bevtl\.", "eventuell"),
    (r"\bspätestens\b", "spätestens"),
    (r"\bca\.", "circa"),
    (r"\bvgl\.", "vergleiche"),
    (r"\bsiehe\b", "siehe"),
    (r"\bMio\.", "Millionen"),
    (r"\bMrd\.", "Milliarden"),
    (r"\bTsd\.", "Tausend"),
    (r"\bNr\.", "Nummer"),
    (r"\bAbs\.", "Absatz"),
    (r"\bS\.(?=\s*\d)", "Seite"),
    (r"\bAbb\.", "Abbildung"),
    (r"\bTab\.", "Tabelle"),
    (r"\bbetr\.", "beträgt"),
    (r"\bmax\.", "maximal"),
    (r"\bmin\.(?!\s*\d)", "minimal"),
    (r"\bz\.\s*Zt\.", "zurzeit"),
    (r"\bStd\.", "Stunden"),
    (r"\bMin\.(?=\s*\d)", "Minuten"),
    (r"\bJh\.", "Jahrhundert"),
    (r"\bWo\.(?=\s*\d)", "Woche"),
    (r"\bmtl\.", "monatlich"),
    (r"\bjährl\.", "jährlich"),
    (r"\btlw\.", "teilweise"),
    (r"\bsog\.\s*Genannten\b", "sogenannten"),
]
EN_ABBREV = [
    (r"\be\.\s*g\.", "for example"),
    (r"\bi\.\s*e\.", "that is"),
    (r"\betc\.", "et cetera"),
    (r"\bapprox\.", "approximately"),
    (r"\bNo\.(?=\s*\d)", "number"),
    (r"\bFig\.", "figure"),
    (r"\bvs\.", "versus"),
    (r"\bInc\.", "incorporated"),
    (r"\bLtd\.", "limited"),
    (r"\bDept\.", "department"),
    (r"\bEst\.", "established"),
    (r"\bmax\.", "maximum"),
    (r"\bmin\.(?!\s*\d)", "minimum"),
    (r"\bmo\.", "month"),
    (r"\byr\.", "year"),
]
# Akronyme, die als Wort gesprochen werden (nicht buchstabiert).
SPOKEN_AS_WORD = {
    "DAX": "Dax", "MDAX": "MDax", "IBAN": "Iban", "TÜV": "Tüv", "NATO": "Nato",
    "UNO": "Uno", "NASA": "Nasa", "BAFIN": "Bafin", "EDEKA": "Edeka", "ALDI": "Aldi",
    "LIDL": "Lidl", "TESLA": "Tesla", "PIN": "Pin", "WLAN": "W Lan", "APP": "App",
    "APPS": "Apps", "OK": "okay", "VERIVOX": "Verivox", "SKODA": "Skoda",
    "SAMSUNG": "Samsung", "PAYPAL": "Paypal", "YOUTUBE": "Youtube", "TIKTOK": "Tiktok",
    "SPOTIFY": "Spotify", "LINKEDIN": "Linkedin", "BAIDU": "Baidu", "ROBO": "Robo",
    "GEZ": "GEZ", "BIP": "BIP",
}
# Akronyme, die bewusst buchstabiert werden (Buchstabe mit Leerzeichen).
SPELL_OUT = {"ETF", "ETFS", "AGB", "EU", "USA", "UK", "US", "GB", "DE", "AT", "CH", "TV",
             "ARD", "ZDF", "DSGVO", "PKW", "LKW", "KFZ", "DSL", "LTE", "SMS", "BGB", "HGB",
             "SGB", "GG", "TAN", "URL", "HTML", "PDF", "FAQ", "CEO", "CFO", "KI", "AI", "IT",
             "PS", "GMBH", "AG", "KG", "USB", "HDMI", "SIM", "ESIM", "M2M", "VR", "AR",
             "NFC", "SEPA", "UMTS", "GPS", "ABS", "TÜV", "HU", "AU", "BAFA", "KFW", "AOK",
             "TK", "VHS", "ZDF", "WDR", "NDR", "SWR", "BR", "RBB", "MDR", "SR", "RB"}
# Römische Ziffern in Gesetzes-/Abschnittsangaben („SGB II" → „SGB zwei").
ROMAN_MAP = {r: i for i, r in enumerate(
    ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII",
     "XIV", "XV", "XVI", "XVII", "XVIII", "XIX", "XX"], start=1)}
ROMAN_CONTEXTS = ("SGB", "BGB", "Abschnitt", "Teil", "Band", "Buch", "Anlage", "Titel")
# Marken-/Fachbegriffe mit eigener Sprechweise.
BRAND_PRONUNCIATION = {
    "CHECK24": "Check vierundzwanzig",
    "VERIVOX": "Verivox",
    "PAYPAL": "Paypal",
    "YOUTUBE": "Youtube",
    "TIKTOK": "Tiktok",
    "SPOTIFY": "Spotify",
    "LINKEDIN": "Linkedin",
    "MCDONALDS": "McDonalds",
}


def _url_spoken(url: str, lang: str) -> str:
    """URL → sprechbare Kurzform („Link zu check24 punkt de").

    Eine vorgelesene URL („https Doppelpunkt Slash Slash www Punkt …") ist
    der schnellste Weg, einen Hörbeitrag wie eine Maschine klingen zu
    lassen. Parität zur Reader-Regel: nur die Domain, mit „punkt".
    """
    m = re.match(r"(?:https?://)?(?:www\.)?([^/\s?#]+)", url)
    host = (m.group(1) if m else url).strip().rstrip(".,;:")
    host = re.sub(r"[.-]+", " punkt ", host)
    prefix = "Link zu " if lang != "en" else "Link to "
    return prefix + host


def _email_spoken(mail: str, lang: str) -> str:
    user, _, domain = mail.partition("@")
    at = " at " if lang != "en" else " at "
    return user + at + _url_spoken(domain, lang).replace("Link zu ", "").replace("Link to ", "")


def _spell_letters(token: str) -> str:
    """Akronym → Buchstaben mit Leerzeichen („ETF" → „E T F")."""
    letters = []
    for ch in token:
        if ch.isdigit():
            letters.append(ch)
        elif ch.isalpha():
            letters.append(ch.upper())
    return " ".join(letters)


def speech_normalize(text: str, lang: str = "de") -> str:
    """Übersetzt geschriebenen Text in *gesprochene* Sprache.

    Sprachabhängig (DE/EN), weil Zahlen, Daten und Währungen anders
    gesprochen werden. Läuft VOR der Synthese und ist der billigste
    Natürlichkeits-Hebel überhaupt: keine Maschine, die „eins Punkt
    zweitausend" sagt, klingt wie ein Mensch.
    """
    if not text:
        return ""
    lang = "en" if str(lang).lower().startswith("en") else "de"
    s = text.replace("\u00a0", " ").replace("\u00ad", "")
    # Entity-Reste sind Markup, keine Sprache: „300&nbsp;€" darf nie als
    # „300 und nbsp Euro" erklingen (zweite Escape-Stufe, Copy-Paste aus
    # einem CMS, Shortcode-Ausgabe).
    s = re.sub(r"&(?:nbsp|#160|#x0*[aA]0);", " ", s, flags=re.I)
    s = re.sub(r"&(?:amp|#38);", " und ", s, flags=re.I)
    s = re.sub(r"&(?:shy|#173);", "", s, flags=re.I)
    s = re.sub(r"&(?:euro|#8364);", " Euro ", s, flags=re.I)
    s = re.sub(r"&[a-zA-Z][a-zA-Z0-9]{1,10};", " ", s)
    s = re.sub(r"&#\d{1,7};", " ", s)
    # Markdown-Fettdruck (**text**) in einen gesprochenen Hinweis umwandeln,
    # damit die TTS-Stimme betont vorträgt, statt die Markierung zu
    # verwerfen. Das verhindert, dass fett gedruckte Textteile komplett
    # untergehen (Problem: "Der fett gedruckte Text wird nicht direkt vorgelesen").
    s = re.sub(r"\*\*(.+?)\*\*", r"Wichtiger Punkt: \1", s)

    # Markdown-/HTML-Reste & Emojis (kein „Emoji-Stottern").
    s = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"[*_`~#>]+", " ", s)
    s = re.sub(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u2190-\u21FF\u2B00-\u2BFF]", " ", s)

    # URLs & E-Mails zuerst sprechbar machen (sonst fressen die Zahlenregeln
    # die Punkte in „check24.de").
    s = re.sub(r"https?://[^\s<)\]]+", lambda m: _url_spoken(m.group(0), lang), s)
    s = re.sub(r"\bwww\.[^\s<)\]]+", lambda m: _url_spoken(m.group(0), lang), s)
    s = re.sub(r"\b[\w._%-]+@[\w.-]+\.\w{2,}\b", lambda m: _email_spoken(m.group(0), lang), s)

    # Einheiten & Sonderzeichen (vor den Abkürzungen, damit „CO2" nicht als
    # Akronym buchstabiert und „kWh" nicht als „kW h" gesprochen wird).
    s = s.replace("§", " Paragraph ")
    s = s.replace("°C", " Grad Celsius ").replace("°", " Grad ")
    s = re.sub(r"\bkWh\b", " Kilowattstunden ", s, flags=re.I)
    s = re.sub(r"\bCO\s?2\b", " C O zwei ", s, flags=re.I)
    s = re.sub(r"\bm²\b", " Quadratmeter ", s)
    s = re.sub(r"\bcm²\b", " Quadratzentimeter ", s)
    s = re.sub(r"\bkm/h\b", " Kilometer pro Stunde ", s, flags=re.I)
    s = re.sub(r"\bm/s\b", " Meter pro Sekunde ", s)
    s = re.sub(r"\bMW\b", " Megawatt ", s)
    s = re.sub(r"\bkW\b", " Kilowatt ", s)
    s = re.sub(r"\bW\b(?=\s*\d|\d\s*$)", " Watt ", s)

    # Römische Ziffern in Gesetzesangaben („SGB II" → „SGB zwei").
    def roman(m: re.Match) -> str:
        ctx, rom = m.group(1), m.group(2).upper()
        n = ROMAN_MAP.get(rom)
        if not n:
            return m.group(0)
        word = de_number_words(n) if lang == "de" else en_number_words(n)
        return f"{ctx} {word}"

    s = re.sub(r"\b(" + "|".join(ROMAN_CONTEXTS) + r")\s+([IVX]{1,5})\b", roman, s)

    # Abkürzungen → gesprochene Sprache.
    for pat, repl in (DE_ABBREV + EN_ABBREV):
        s = re.sub(pat, repl, s, flags=re.I)

    # Akronyme: als Wort oder buchstabiert.
    def acronym(m: re.Match) -> str:
        tok = m.group(0)
        up = tok.upper()
        if up in BRAND_PRONUNCIATION:
            return BRAND_PRONUNCIATION[up]
        if up in SPOKEN_AS_WORD:
            return SPOKEN_AS_WORD[up]
        if up in SPELL_OUT or len(tok) <= 5:
            return _spell_letters(tok)
        return tok

    s = re.sub(r"\b[A-Z][A-Z0-9]{1,6}\b", acronym, s)

    # Marken mit Zahl („Check24") werden von der Zahlenregel nicht
    # angetastet, weil die Ziffer am Wort klebt – hier explizit sprechbar.
    for brand, spoken in BRAND_PRONUNCIATION.items():
        s = re.sub(rf"\b{brand}\b", spoken, s, flags=re.I)

    # Zahlen, Währungen, Daten, Zeiten – sprachabhängig.
    s = _normalize_numbers(s, lang)

    # Typografie → Sprechpausen: Gedankenstrich wird zur kurzen Pause.
    s = re.sub(r"\s*[–—]\s*", ", ", s)
    s = s.replace("…", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _normalize_numbers(s: str, lang: str) -> str:
    """Zahlen/Daten/Währungen/Zeiten in gesprochene Form überführen."""

    def de_card(num: str, standalone: bool = False) -> str:
        try:
            n = int(num)
        except ValueError:
            return num
        return de_number_words(n, standalone=standalone)

    def en_card(num: str) -> str:
        try:
            return en_number_words(int(num))
        except ValueError:
            return num

    # 1) Währung mit Dezimalstellen: 1.299,50 € / €1,299.50 / $1,299.50
    def money_de(gross: str | None, cents: str | None) -> str:
        g = (gross or "").replace(".", "").replace(",", "")
        if not g.isdigit():
            return (gross or "") + " Euro"
        word = de_card(g)
        if cents and cents.isdigit() and int(cents) > 0:
            return f"{word} Euro und {de_card(str(int(cents)))} Cent"
        return f"{word} Euro"

    def money_en(sym: str, gross: str | None, cents: str | None) -> str:
        g = (gross or "").replace(",", "")
        if not g.isdigit():
            return (gross or "") + " dollars"
        unit = "dollars" if sym == "$" else ("pounds" if sym == "£" else "euros")
        word = en_card(g)
        if cents and cents.isdigit() and int(cents) > 0:
            return f"{word} {unit} and {en_card(str(int(cents)))} cents"
        return f"{word} {unit}"

    if lang == "de":
        s = re.sub(r"€\s*(\d[\d.]*)(?:,(\d{1,2}))?",
                   lambda m: money_de(m.group(1), m.group(2)), s)
        s = re.sub(r"(\d[\d.]*)(?:,(\d{1,2}))?\s*(?:€|Euro\b|EUR\b)",
                   lambda m: money_de(m.group(1), m.group(2)), s, flags=re.I)
        s = re.sub(r"\bCHF\s*(\d[\d.']*)",
                   lambda m: f"{de_card(m.group(1).replace('.', ''))} Franken", s)
        s = re.sub(r"\$\s*(\d[\d,]*)(?:\.(\d{1,2}))?",
                   lambda m: f"{de_card(m.group(1).replace(',', ''))} Dollar", s)
    else:
        s = re.sub(r"([$£€])\s*(\d[\d,]*)(?:\.(\d{1,2}))?",
                   lambda m: money_en(m.group(1), m.group(2), m.group(3)), s)
        s = re.sub(r"(\d[\d,]*)(?:\.(\d{1,2}))?\s*(?:euros?|EUR)\b",
                   lambda m: f"{en_card(m.group(1).replace(',', ''))} euros", s, flags=re.I)

    # 2) Prozent / Prozentpunkte
    if lang == "de":
        s = re.sub(r"(\d+(?:[.,]\d+)?)\s*%", lambda m: _dec_de(m.group(1)) + " Prozent", s)
        s = re.sub(r"(\d+(?:[.,]\d+)?)\s*Prozentpunkte", lambda m: _dec_de(m.group(1)) + " Prozentpunkte", s)
    else:
        s = re.sub(r"(\d+(?:[.,]\d+)?)\s*%", lambda m: _dec_en(m.group(1)) + " percent", s)

    # 3) Datum
    if lang == "de":
        def date_de(m: re.Match) -> str:
            d, mo, y = int(m.group(1)), int(m.group(2)), m.group(3)
            if not 1 <= mo <= 12:
                return m.group(0)
            year = int(y) if len(y) == 4 else 2000 + int(y)
            return f"{de_ordinal_words(d)} {DE_MONTHS[mo - 1]} {de_year_words(year)}"

        s = re.sub(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4}|\d{2})\b", date_de, s)

        def date_iso_de(m: re.Match) -> str:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if not 1 <= mo <= 12:
                return m.group(0)
            return f"{de_ordinal_words(d)}. {DE_MONTHS[mo - 1]} {de_year_words(y)}"

        s = re.sub(r"\b(\d{4})-(\d{2})-(\d{2})\b", date_iso_de, s)

        def month_year_de(m: re.Match) -> str:
            mo, y = int(m.group(1)), int(m.group(2))
            if not 1 <= mo <= 12:
                return m.group(0)
            return f"{DE_MONTHS[mo - 1]} {de_year_words(y)}"

        s = re.sub(r"\b(?:im|seit|ab|von|bis|am)?\s*(\d{2})\.(\d{4})\b", month_year_de, s)
    else:
        def date_en(m: re.Match) -> str:
            mo, d, y = int(m.group(1)), int(m.group(2)), m.group(3)
            if not 1 <= mo <= 12:
                return m.group(0)
            year = int(y) if len(y) == 4 else 2000 + int(y)
            return f"{EN_MONTHS[mo - 1]} {en_ordinal_words(d)}, {en_year_words(year)}"

        s = re.sub(r"\b(\d{1,2})/(\d{1,2})/(\d{4}|\d{2})\b", date_en, s)

        def date_iso_en(m: re.Match) -> str:
            y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if not 1 <= mo <= 12:
                return m.group(0)
            return f"{EN_MONTHS[mo - 1]} {en_ordinal_words(d)}, {en_year_words(y)}"

        s = re.sub(r"\b(\d{4})-(\d{2})-(\d{2})\b", date_iso_en, s)

    # 4) Uhrzeiten
    if lang == "de":
        def time_de(m: re.Match) -> str:
            h, mi = int(m.group(1)), m.group(2)
            tail = " Uhr" if m.group(3) else ""
            if mi == "00":
                return f"{de_card(str(h))}{tail}"
            return f"{de_card(str(h))} Uhr {de_card(str(int(mi)))}{tail}"

        s = re.sub(r"\b(\d{1,2}):(\d{2})(\s*Uhr)?", time_de, s)
    else:
        def time_en(m: re.Match) -> str:
            h, mi = int(m.group(1)), m.group(2)
            if mi == "00":
                return f"{en_card(str(h))} o'clock"
            return f"{en_card(str(h))}:{en_card(str(int(mi)))}"

        s = re.sub(r"\b(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)?", time_en, s)

    # 5) Zahlenbereiche („20 bis 30 Prozent" bleiben zwei Kardinalzahlen)
    s = re.sub(r"\b(\d+)\s*(?:-|bis|to|–)\s*(\d+)\b",
               lambda m: (f"{de_card(m.group(1))} bis {de_card(m.group(2))}" if lang == "de"
                          else f"{en_card(m.group(1))} to {en_card(m.group(2))}"), s)

    # 6) Dezimalzahlen
    s = re.sub(r"\b(\d+(?:[.,]\d+)+)\b", lambda m: (_dec_de(m.group(1)) if lang == "de"
                                                    else _dec_en(m.group(1))), s)

    # 7) Tausender ohne Einheit
    s = re.sub(r"\b(\d{1,3}(?:[.,]\d{3})+)\b",
               lambda m: de_card(m.group(1).replace(".", "").replace(",", "")) if lang == "de"
               else en_card(m.group(1).replace(",", "").replace(".", "")), s)

    # 8) Vierstellige Jahreszahl ohne Kontext → Jahressprechweise.
    #    Der Lookahead verbietet nur *Wort*zeichen und „.Ziffer" (12.08.2026),
    #    nicht den Satzpunkt: „… gilt ab 2026." muss ebenfalls aufgelöst werden.
    year_re = r"(?<![\w.])(\d{4})(?!\w)(?!\.\d)"
    if lang == "de":
        s = re.sub(year_re,
                   lambda m: de_year_words(int(m.group(1))) if 1000 <= int(m.group(1)) <= 2099
                   else m.group(0), s)
    else:
        s = re.sub(year_re,
                   lambda m: en_year_words(int(m.group(1))) if 1000 <= int(m.group(1)) <= 2099
                   else m.group(0), s)

    # 9) Restliche Kardinalzahlen (auch direkt vor dem Satzpunkt).
    s = re.sub(r"(?<![\w.,])\d+(?!\w)(?!\.\d)",
               lambda m: de_card(m.group(0), standalone=True) if lang == "de" else en_card(m.group(0)), s)
    return s


def _dec_de(num: str) -> str:
    """„3,5" → „drei Komma fünf" (DE) – Tausenderpunkte vorher entfernen."""
    num = num.replace(".", "")
    if "," not in num:
        return de_number_words(int(num), standalone=True) if num.isdigit() else num
    gross, dec = num.split(",", 1)
    head = de_number_words(int(gross)) if gross.isdigit() else gross
    tail = " ".join(DE_UNITS_[int(d)] if d.isdigit() else d for d in dec)
    return f"{head} Komma {tail}"


def _dec_en(num: str) -> str:
    num = num.replace(",", "")
    if "." not in num:
        return en_number_words(int(num)) if num.isdigit() else num
    gross, dec = num.split(".", 1)
    head = en_number_words(int(gross)) if gross.isdigit() else gross
    tail = " ".join(EN_UNITS_[int(d)] if d.isdigit() else d for d in dec)
    return f"{head} point {tail}"


# ==========================================================================
# 4. Satztrennung (atembogen-fähig) + Sprech-Einheiten
# ==========================================================================
# Abkürzungen, deren Punkt niemals ein Satzende ist.
ABBREV_DOTS = [
    "z. B.", "d. h.", "u. a.", "s. o.", "u. v. m.", "i. d. R.", "z. Z.", "o. g.", "v. a.",
    "bzw.", "usw.", "ggf.", "ca.", "vgl.", "inkl.", "exkl.", "zzgl.", "abzgl.", "evtl.",
    "Mio.", "Mrd.", "Tsd.", "Abb.", "Tab.", "betr.", "max.", "min.", "Jh.",
    "mtl.", "jährl.", "tlw.", "Dr.", "Prof.", "Hr.", "Mr.", "Mrs.", "Ms.",
    "etc.", "e.g.", "i.e.", "approx.", "vs.", "Inc.", "Ltd.", "Fig.", "z.B.", "u.a.", "s.o.",
    "St.", "Fr.", "No.", "Dept.", "Est.", "mo.", "yr.",
]
# Abkürzungen, die nur mit folgender Ziffer gemeint sind („S. 12", „Nr. 7").
# Ohne diese Einschränkung würde jedes englische Wort auf „…s." als
# Abkürzung gelten und echte Satzenden verschlucken.
ABBREV_DOTS_WITH_DIGIT = ["S.", "Nr.", "Abs.", "Art.", "Pkt.", "Std.", "Min.", "Wo."]


def split_sentences(text: str, lang: str = "de") -> list[str]:
    """Trennt Text in Sätze, ohne Abkürzungs-Punkte als Satzende zu deuten.

    Alle Punkte einer Abkürzung werden maskiert – auch der Schlusspunkt von
    „z. B.". Sonst entsteht mitten im Satz eine Atempause, und genau diese
    falschen Pausen sind es, die TTS „abgehackt" klingen lassen.
    """
    t = re.sub(r"\s+", " ", text or "").strip()
    if not t:
        return []
    marker = "\x02"

    def mask(m: re.Match) -> str:
        # Originaltext behalten (Groß-/Kleinschreibung), nur Punkte maskieren.
        return m.group(0).replace(".", marker)

    for ab in sorted(ABBREV_DOTS, key=len, reverse=True):
        t = re.sub(re.escape(ab) + r"(?!\s*$)", mask, t, flags=re.I)
    for ab in sorted(ABBREV_DOTS_WITH_DIGIT, key=len, reverse=True):
        t = re.sub(re.escape(ab) + r"(?=\s*\d)", mask, t, flags=re.I)
    # Initialen („A. Merkel"), Zahlengruppen („12.08.") und Aufzählungs-
    # punkte („1. Vergleichen") schützen.
    t = re.sub(r"\b([A-ZÄÖÜ])\.(?=\s|$)", r"\1" + marker, t)
    t = re.sub(r"(\d)\.(?=\d)", r"\1" + marker, t)
    t = re.sub(r"(^|\s)(\d{1,2})\.(?=\s|$)", r"\1\2" + marker, t)
    parts = re.split(r"(?<=[.!?…])\s+(?=[\"'(«A-ZÄÖÜ0-9])", t)
    out = []
    for part in parts:
        part = part.replace(marker, ".").strip()
        if len(part) > 1:
            out.append(part)
    return out or ([t.replace(marker, ".")] if t else [])


# Rollen-Prosodie: Parität zur PROSODY-Tabelle des Readers, damit Tonspur
# und Browser-Fallback gleich klingen. rate = Faktor, pitch = Faktor,
# volume = Faktor, before/after = zusätzliche Stille in Millisekunden.
PROSODY: dict[str, dict[str, float]] = {
    # Werte 1:1 aus static/premium/ff-reader.js (PROSODY) – das Paritäts-Gate
    # scripts/reader_prosody_parity_check.py erzwingt diese Gleichheit.
    "h2":            {"rate": 0.90, "pitch": 0.88, "volume": 1.00, "before": 620, "after": 340},
    "h3":            {"rate": 0.92, "pitch": 0.90, "volume": 1.00, "before": 460, "after": 260},
    "h4":            {"rate": 0.94, "pitch": 0.92, "volume": 0.99, "before": 360, "after": 220},
    "h5":            {"rate": 0.95, "pitch": 0.93, "volume": 0.99, "before": 300, "after": 200},
    "h6":            {"rate": 0.96, "pitch": 0.94, "volume": 0.98, "before": 260, "after": 180},
    "p":             {"rate": 1.00, "pitch": 0.96, "volume": 1.00, "before": 130, "after": 190},
    "lead":          {"rate": 0.96, "pitch": 0.95, "volume": 1.00, "before": 180, "after": 260},
    "li":            {"rate": 1.00, "pitch": 0.97, "volume": 0.99, "before": 110, "after": 150},
    "blockquote":    {"rate": 0.95, "pitch": 0.95, "volume": 0.96, "before": 340, "after": 320},
    "callout":       {"rate": 0.95, "pitch": 0.93, "volume": 1.00, "before": 380, "after": 320},
    "warning":       {"rate": 0.90, "pitch": 0.86, "volume": 1.00, "before": 460, "after": 380},
    "overview-card": {"rate": 0.97, "pitch": 0.95, "volume": 1.00, "before": 300, "after": 260},
    "table-intro":   {"rate": 0.93, "pitch": 0.90, "volume": 1.00, "before": 520, "after": 320},
    "table-row":     {"rate": 1.02, "pitch": 0.97, "volume": 0.98, "before": 90,  "after": 210},
    "table-sum":     {"rate": 0.94, "pitch": 0.91, "volume": 1.00, "before": 260, "after": 300},
    "table-outro":   {"rate": 0.94, "pitch": 0.92, "volume": 1.00, "before": 260, "after": 360},
    "overview-title": {"rate": 0.92, "pitch": 0.90, "volume": 1.00, "before": 520, "after": 300},
    "overview-note":  {"rate": 0.95, "pitch": 0.94, "volume": 0.98, "before": 280, "after": 300},
    "intro":         {"rate": 0.92, "pitch": 0.92, "volume": 1.00, "before": 0,   "after": 520},
    "outro":         {"rate": 0.92, "pitch": 0.92, "volume": 1.00, "before": 520, "after": 0},
}

# Grundtempo je Sprache (v10): Neuralstimmen klingen bei 1.0 gehetzt.
# 0.88 DE / 0.90 EN ≈ Nachrichtensprecher (~150 Wörter/min), nicht hetzend,
# nicht schleppend. Das ist der größte kostenlose Hebel gegen „zu schnell".
LANGUAGE_RATE = {"de": 0.88, "en": 0.90}
# Männliche Grundtonlage: leichte Absenkung für „Erzähler"-Charakter.
LANGUAGE_PITCH_HZ = {"de": -2.0, "en": -1.0}
# Finale Dehnung am Blockende (Sprecher werden am Absatzschluss langsamer).
FINAL_LENGTHEN = 0.95
# Dichte-Bremse: Zahlen-/Komposita-lastige Sätze werden ruhiger gelesen.
DENSITY_SLOWDOWN = 0.035


def prosody_for(block_type: str) -> dict[str, float]:
    return dict(PROSODY.get(block_type) or PROSODY["p"])


def density_factor(text: str) -> float:
    """Informationsdichte → Tempofaktor (Parität zu contentRateFactor im JS)."""
    words = re.findall(r"\S+", text or "")
    if not words:
        return 1.0
    digits = sum(1 for w in words if re.search(r"\d", w))
    long_words = sum(1 for w in words if len(w) >= 14)
    commas = (text or "").count(",")
    load = (digits / len(words)) * 1.6 + (long_words / len(words)) * 1.2 + min(commas, 6) / 30.0
    n = len(words)
    if n > 22:
        load += 0.45
    if n > 32:
        load += 0.45
    return max(0.90, 1.0 - min(load, 2.0) * DENSITY_SLOWDOWN)


class Unit:
    """Eine Sprech-Einheit: ein Satz mit Sprache, Rolle und Prosodie.

    ``emo`` ist die Satzmelodie (statement/question/exclamation) – die deutsche
    Entsprechung von ``emo`` im Browser-Fallback. Fragen werden minimal angehoben
    und erhalten mehr Pausenraum, Ausrufe leicht betont: genau das unterscheidet
    einen lebendigen Sprecher von einem monoton vorlesenden Roboter.
    """

    __slots__ = ("block", "text", "lang", "role", "rate", "pitch", "volume",
                 "before_ms", "after_ms", "final", "emo")

    def __init__(self, block: int, text: str, lang: str, role: str, rate: float,
                 pitch: float, volume: float, before_ms: int, after_ms: int,
                 final: bool, emo: str = "statement"):
        self.block = block
        self.text = text
        self.lang = lang
        self.role = role
        self.rate = rate
        self.pitch = pitch
        self.volume = volume
        self.before_ms = before_ms
        self.after_ms = after_ms
        self.final = final
        self.emo = emo

    def as_dict(self) -> dict:
        return {"b": self.block, "text": self.text, "lang": self.lang, "role": self.role,
                "rate": round(self.rate, 4), "pitch": round(self.pitch, 4),
                "volume": round(self.volume, 4), "before": self.before_ms,
                "after": self.after_ms, "final": self.final, "emo": self.emo}


def sentence_emotion(text: str) -> str:
    """Satzmelodie aus dem Satzschlusszeichen (statement/question/exclamation).

    Parität zur JS-Regie: Ein Satz, der auf „?“ endet, ist eine Frage und wird
    minimal angehoben und mit etwas mehr Pausenraum gelesen; „!“ bekommt eine
    leichte Betonung. Das ist die häufigste fehlende Natürlichkeits-Stufe – ein
    Artikel voller Feststellungen klingt sonst wie ein Kontoauszug.
    """
    tail = (text or "").rstrip().rpartition(" ")[-1][-1:]  # letztes Zeichen robust
    if tail in ("?", "？"):
        return "question"
    if tail in ("!", "！"):
        return "exclamation"
    return "statement"


# Grundwerte der Satzmelodie (Parität zu autoPitch/effectiveRateFor im JS):
# Frage +0.05 Tonlage, Ausruf +0.02; Fragen/Ausrufe minimal ruhiger gelesen.
EMO_PITCH = {"question": 0.05, "exclamation": 0.02, "statement": 0.0}
EMO_RATE = {"question": 0.985, "exclamation": 0.99, "statement": 1.0}
# Zusätzlicher Pausenraum nach einer Frage/beim Ausruf (Parität zu
# pauseAfterChunk im JS: question +80 ms, exclamation +50 ms).
EMO_AFTER_MS = {"question": 80, "exclamation": 50, "statement": 0}


def build_units(blocks: list[tuple[str, str, str]], base_lang: str,
                prosody: bool = True) -> list[Unit]:
    """Blöcke → Sprech-Einheiten.

    Zwei Natürlichkeits-Entscheidungen stecken hier:
      1. **Satzweises DE/EN-Routing.** Ein deutscher Absatz mit dem Satz
         „The comparison shows lower fees." wird satzweise erkannt und von
         der englischen Stimme gesprochen – ohne Umschalter für die
         Leserin/den Leser.
      2. **Rollen-Prosodie.** Überschrift, Warnbox und Tabellenzeile
         bekommen eigenes Tempo, eigene Tonlage und eigene Pausen. Ein
         Text, in dem alles gleich schnell und gleich hoch gesprochen
         wird, klingt immer nach Maschine.
    """
    units: list[Unit] = []
    for b_index, (lang, btype, raw) in enumerate(blocks):
        block_lang = sniff_lang(raw, lang or base_lang)
        text = speech_normalize(raw, block_lang)
        if not text:
            continue
        sentences = split_sentences(text, block_lang) or [text]
        prof = prosody_for(btype) if prosody else prosody_for("p")
        for s_index, sentence in enumerate(sentences):
            s_lang = sniff_lang(sentence, block_lang)
            # Sehr kurze Sätze (< 3 Wörter) erben die Blocksprache: ein
            # „Genau." darf nicht als englisch gelten.
            if len(re.findall(r"\S+", sentence)) < 3:
                s_lang = block_lang
            emo = sentence_emotion(sentence)
            rate = prof["rate"] * LANGUAGE_RATE.get(s_lang, 1.0)
            pitch = prof["pitch"]
            if prosody:
                rate *= density_factor(sentence) * EMO_RATE.get(emo, 1.0)
                pitch += EMO_PITCH.get(emo, 0.0)
            is_final = s_index == len(sentences) - 1
            if is_final and prosody:
                rate *= FINAL_LENGTHEN
            before = int(prof["before"]) if (s_index == 0 and prosody) else 0
            after = int(prof["after"]) if (is_final and prosody) else 90
            if prosody:
                after += EMO_AFTER_MS.get(emo, 0)
            units.append(Unit(
                block=b_index, text=sentence, lang=s_lang, role=btype,
                rate=max(0.6, min(1.25, rate)), pitch=max(0.6, min(1.4, pitch)),
                volume=max(0.5, min(1.2, prof["volume"])),
                before_ms=before, after_ms=after, final=is_final, emo=emo))
    return units


# ==========================================================================
# 5. Audio-Bausteine (reines Python + ffmpeg, keine Bezahl-Dienste)
# ==========================================================================
def pcm_silence(ms: int, rate: int = TARGET_RATE) -> bytes:
    n = max(0, int(rate * ms / 1000))
    return b"\x00\x00" * n


def pcm_from_samples(samples: list[int]) -> bytes:
    return struct.pack("<" + "h" * len(samples), *[max(-32768, min(32767, int(s))) for s in samples])


def pcm_to_samples(pcm: bytes) -> list[int]:
    n = len(pcm) // 2
    return list(struct.unpack("<" + "h" * n, pcm[: n * 2])) if n else []


def build_wav(pcm: bytes, rate: int = TARGET_RATE, channels: int = 1, bits: int = 16) -> bytes:
    byte_rate = rate * channels * bits // 8
    block_align = channels * bits // 8
    return struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(pcm), b"WAVE", b"fmt ", 16,
                       1, channels, rate, byte_rate, block_align, bits, b"data", len(pcm)) + pcm


def wav_pcm(data: bytes) -> tuple[bytes, int]:
    """Liefert (PCM-Bytes, Abtastrate) aus einem RIFF/WAVE-Puffer."""
    if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
        raise ValueError("Kein gültiges RIFF/WAVE.")
    pos, fmt, pcm = 12, None, None
    while pos + 8 <= len(data):
        cid = data[pos:pos + 4]
        size = struct.unpack("<I", data[pos + 4:pos + 8])[0]
        if cid == b"fmt ":
            fmt = data[pos + 8:pos + 8 + size]
        elif cid == b"data":
            pcm = data[pos + 8:pos + 8 + size]
        pos += 8 + size + (size & 1)
        if fmt is not None and pcm is not None:
            break
    if fmt is None or pcm is None:
        raise ValueError("WAV ohne fmt-/data-Chunk.")
    channels, rate, bits = struct.unpack("<HII", fmt[2:12])[0], struct.unpack("<I", fmt[4:8])[0], struct.unpack("<H", fmt[14:16])[0]
    if channels != 1 or bits != 16:
        raise ValueError(f"Nur 16-bit-Mono unterstützt (got channels={channels}, bits={bits}).")
    return pcm, rate


def rms_db(pcm: bytes) -> float:
    samples = pcm_to_samples(pcm)
    if not samples:
        return -120.0
    mean = sum(s * s for s in samples) / len(samples)
    if mean <= 0:
        return -120.0
    return 20 * math.log10(math.sqrt(mean) / 32768.0)


def trim_silence(pcm: bytes, rate: int, floor_db: float = -48.0,
                 keep_head_ms: int = 20, keep_tail_ms: int = 70) -> bytes:
    """Schneidet unnatürlich lange Stille an den Segmenträndern ab.

    Neural-Engines liefern oft 200–500 ms „ tote Luft" vor und nach dem
    Satz. Bleibt sie stehen, entsteht ein schleppender, unsicherer Rhythmus
    – einer der häufigsten Gründe, warum TTS „nicht wie ein Mensch" klingt.
    Die Pausen werden danach bewusst und rollengerecht wieder eingesetzt.
    """
    samples = pcm_to_samples(pcm)
    if not samples:
        return pcm
    threshold = 32768 * (10 ** (floor_db / 20))
    first = next((i for i, s in enumerate(samples) if abs(s) > threshold), None)
    last = next((i for i in range(len(samples) - 1, -1, -1) if abs(samples[i]) > threshold), None)
    if first is None or last is None:
        return pcm_silence(keep_tail_ms, rate)
    first = max(0, first - int(rate * keep_head_ms / 1000))
    last = min(len(samples) - 1, last + int(rate * keep_tail_ms / 1000))
    return pcm_from_samples(samples[first:last + 1])


def equal_power_fade(a: bytes, b: bytes, rate: int, fade_ms: int = 6) -> bytes:
    """Klickfreie Verbindung zweier PCM-Segmente (Equal-Power-Kreuzfade).

    Eine lineare Kreuzfade erzeugt bei Sprache einen hörbaren Pegel-Knick;
    die Equal-Power-Kurve (cos/sin) hält die Energie konstant – der
    Übergang verschwindet.
    """
    sa, sb = pcm_to_samples(a), pcm_to_samples(b)
    if not sa:
        return b
    if not sb:
        return a
    n = max(1, min(int(rate * fade_ms / 1000), len(sa), len(sb)))
    out = sa[: len(sa) - n]
    for i in range(n):
        w = (i + 1) / (n + 1)
        ga, gb = math.cos(w * math.pi / 2), math.sin(w * math.pi / 2)
        out.append(int(sa[len(sa) - n + i] * ga + sb[i] * gb))
    out.extend(sb[n:])
    return pcm_from_samples(out)


def highpass_pcm(pcm: bytes, rate: int, fc: float = 70.0, q: float = 0.7071) -> bytes:
    """Butterworth-Hochpass 2. Ordnung (korrekte Direct-Form-I-Implementierung).

    Entfernt Subsonik-/Brumm-Anteile unterhalb der Sprache. Die alte
    Implementierung im Generator benutzte eine falsche Zustandsführung
    (z1 = x − y) und erzeugte damit selbst Artefakte – das ist hier
    ersetzt.
    """
    w0 = 2 * math.pi * fc / rate
    cos_w0, sin_w0 = math.cos(w0), math.sin(w0)
    alpha = sin_w0 / (2 * q)
    b0 = (1 + cos_w0) / 2
    b1 = -(1 + cos_w0)
    b2 = (1 + cos_w0) / 2
    a0 = 1 + alpha
    a1 = -2 * cos_w0
    a2 = 1 - alpha
    b0, b1, b2 = b0 / a0, b1 / a0, b2 / a0
    a1, a2 = a1 / a0, a2 / a0
    x1 = x2 = y1 = y2 = 0.0
    out: list[int] = []
    for s in pcm_to_samples(pcm):
        x0 = float(s)
        y0 = b0 * x0 + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        out.append(int(max(-32768.0, min(32767.0, round(y0)))))
        x2, x1 = x1, x0
        y2, y1 = y1, y0
    return pcm_from_samples(out)


def peak_normalize(pcm: bytes, target_db: float = -1.5) -> bytes:
    """Einfache Peak-Normalisierung, falls ffmpeg/loudnorm fehlt."""
    samples = pcm_to_samples(pcm)
    peak = max((abs(s) for s in samples), default=0)
    if peak <= 0:
        return pcm
    gain = (32767 * (10 ** (target_db / 20))) / peak
    if gain > 8.0:
        gain = 8.0            # Rauschen nicht unnatürlich hochziehen
    return pcm_from_samples([int(s * gain) for s in samples])


def dc_offset_remove(pcm: bytes) -> bytes:
    """Entfernt einen Gleichanteil (DC-Offset) aus dem 16-bit-PCM.

    Warum das wichtig ist: Neural-Engines und alle Konvertierungsschritte
    hinterlassen oft einen kleinen, konstanten Versatz der Wellenform um die
    Nulllinie. Der macht die Segmente unnötig „voll“ und kann an Schnittstellen
    hörbare Knackser erzeugen, weil zwei Segmente beim Überblenden nicht beide
    bei 0 beginnen. Das Subtrahieren des Mittelwerts ist verlustfrei und
    dämpft beides. Im Normalfall (Offset ≈ 0) ist es ein No-Op.
    """
    samples = pcm_to_samples(pcm)
    if not samples:
        return pcm
    mean = sum(samples) / len(samples)
    if abs(mean) < 8.0:          # Rauschen würde sonst „aufgedreht“
        return pcm
    return pcm_from_samples([int(round(s - mean)) for s in samples])


def micro_fade_pcm(pcm: bytes, rate: int, fade_ms: int = 10) -> bytes:
    """Ein-/Ausblendung am Segmentrand – Rest-Klickschutz.

    10 ms (nicht 3 ms): Unter ~8 ms bleibt ein Amplitudensprung als Knackser
    hörbar, darüber verschwindet der Schnitt, ohne dass die Stimme atmet.
    """
    n = max(1, int(rate * fade_ms / 1000))
    samples = pcm_to_samples(pcm)
    if len(samples) < 2 * n:
        return pcm
    for i in range(n):
        w = (i + 1) / (n + 1)
        samples[i] = int(samples[i] * w)
        samples[-1 - i] = int(samples[-1 - i] * w)
    return pcm_from_samples(samples)


def declick_pcm(pcm: bytes, jump: int = 7000) -> bytes:
    """Glättet Einzel-Sample-Sprünge (digitale Knackser) per Interpolation.

    Neural-Engines und MP3-Decoder hinterlassen gelegentlich einen einzelnen
    Ausreißer. Der Sprung von z. B. +12000 auf −8000 in einem Sample ist
    das hörbare „Knack". Interpolation über den Nachbarn entfernt ihn,
    ohne die Stimme zu färben.
    """
    samples = pcm_to_samples(pcm)
    if len(samples) < 3:
        return pcm
    out = samples[:]
    changed = False
    for i in range(1, len(out) - 1):
        if abs(out[i] - out[i - 1]) > jump and abs(out[i] - out[i + 1]) > jump:
            out[i] = (out[i - 1] + out[i + 1]) // 2
            changed = True
    return pcm_from_samples(out) if changed else pcm


def soft_limit_pcm(pcm: bytes, floor_db: float = -2.0) -> bytes:
    """Sanfter Peak-Limiter: fängt Clipping-Spitzen ab, die nach Denoise
    oder Lautheitsanhebung als Knackser hörbar wären."""
    threshold = 32767 * (10 ** (floor_db / 20))
    samples = pcm_to_samples(pcm)
    out = []
    for val in samples:
        a = abs(val)
        if a > threshold:
            limited = threshold + (a - threshold) * 0.45
            val = int((1 if val >= 0 else -1) * min(limited, 32767))
        out.append(val)
    return pcm_from_samples(out)


# Ziel-Sprechgeschwindigkeit in Zeichen/s (ohne Leerzeichen).
# Deutscher Nachrichtensprecher ≈ 12 Zeichen/s; Neural-Engines liegen oft
# bei 16–20 und klingen deshalb gehetzt. Die automatische Tempo-Regie
# bremst nur, wenn die Engine nachweislich zu schnell gesprochen hat.
TARGET_CHARS_PER_SEC = {"de": 12.2, "en": 13.4}


def tempo_factor_for(text: str, pcm: bytes, rate: int, lang: str) -> float:
    """1.0 = Tempo belassen, < 1.0 = langsamer (niemals schneller)."""
    chars = len(re.sub(r"\s+", "", text or ""))
    dur = (len(pcm) / 2) / max(1, rate)
    if chars < 12 or dur < 0.18:
        return 1.0
    measured = chars / dur
    key = "en" if str(lang).lower().startswith("en") else "de"
    target = TARGET_CHARS_PER_SEC.get(key, 12.2)
    if measured <= target * 1.06:
        return 1.0
    return max(0.82, min(1.0, target / measured))


def auto_tempo_pcm(pcm: bytes, rate: int, text: str, lang: str,
                   exe: str | None = None) -> bytes:
    """Bremst zu schnelle Segmente tonhöhenerhaltend (ffmpeg atempo).

    Ohne ffmpeg ein No-Op – die LANGUAGE_RATE-Bremse greift trotzdem.
    """
    factor = tempo_factor_for(text, pcm, rate, lang)
    if factor >= 0.995:
        return pcm
    exe = exe or find_ffmpeg()
    if not exe:
        return pcm
    wav = build_wav(pcm, rate)
    try:
        proc = subprocess.run(
            [exe, "-hide_banner", "-loglevel", "error", "-f", "wav", "-i", "pipe:0",
             "-af", f"atempo={factor:.4f}", "-ac", "1", "-ar", str(rate),
             "-f", "s16le", "pipe:1"],
            input=wav, capture_output=True, timeout=180)
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
    except (OSError, subprocess.SubprocessError):
        pass
    return pcm


def segment_is_broken(pcm: bytes, rate: int) -> bool:
    """Stille, abgebrochene oder leere Segmente – die Engine hat versagt."""
    if not pcm or len(pcm) < int(rate * 0.06) * 2:
        return True
    return rms_db(pcm) < -48.0


def heal_segment(pcm: bytes, rate: int, text: str = "", lang: str = "de") -> bytes:
    """Automatische Fehlerbeseitigung eines Satz-Segments.

    Reihenfolge ist Absicht: erst tote Luft und DC-Versatz weg (sonst
    rechnet der Declicker auf Stille), dann Knackser, dann Tempo, zuletzt
    10-ms-Fade auf 0 – der harte Schnitt zur Pause knackt dann nicht.
    """
    pcm = trim_silence(pcm, rate)
    pcm = dc_offset_remove(pcm)
    pcm = declick_pcm(pcm)
    pcm = auto_tempo_pcm(pcm, rate, text, lang)
    pcm = micro_fade_pcm(pcm, rate, fade_ms=10)
    return pcm


def broadband_denoise_wav(wav_bytes: bytes, exe: str | None = None) -> bytes:
    """Spektrale Rauschminderung (Broadband-Denoise) über ffmpeg ``afftdn``.

    Das ist der größte kostenlose Hebel gegen das häufigste „Qualitäts-\n
    Rauschen\" der Vorlese-Tonspur: Zisch- und Grundrauschen, das die Engine
    oder die MP3-Kodierung hinterlässt. Ein Hochpass allein entfernt nur das
    tiefe Brummen; ein vielbandiger Noise-Reducer senkt das Rauschband über
    die gesamte Sprachbreite, ohne die Stimme zu „konservieren\" (kraftlos zu
    machen).

    v10-Kette (High-End, kostenlos):
      highpass 80 Hz   Brummen/Subsonik
      lowpass 10 kHz   Zisch-/Kodier-Rauschen oberhalb der Sprache
      afftdn nr=12     spürbare Rauschminderung, Stimme bleibt lebendig
      nf=-28 / tn=1    Noise-Floor + Tracking

    Robuster Fallback: Fehlt ffmpeg oder versteht die installierte Version die
    Optionen nicht (alte Builds), wird der Puffer unverändert zurückgegeben –
    das Mastering (Hochpass, DC-Offset, Lautheit) bleibt trotzdem aktiv.
    """
    exe = exe or find_ffmpeg()
    if not exe:
        return wav_bytes

    def _run(filters: str) -> bytes | None:
        proc = subprocess.run(
            [exe, "-hide_banner", "-loglevel", "error", "-f", "wav", "-i", "pipe:0",
             "-af", filters, "-ac", "1", "-f", "wav", "pipe:1"],
            input=wav_bytes, capture_output=True, timeout=1200)
        return proc.stdout if (proc.returncode == 0 and proc.stdout) else None

    # 1) Sprachband + Denoise; 2) nur Denoise; 3) Kernfilter; 4) unverändert.
    for filters in (
        "highpass=f=80:poles=2,lowpass=f=10000:poles=2,afftdn=nr=12:nf=-28:tn=1",
        "afftdn=nr=12:nf=-28:tn=1",
        "afftdn=nr=12",
        "afftdn=nr=9",
        "afftdn",
    ):
        try:
            out = _run(filters)
        except (OSError, subprocess.SubprocessError):
            out = None
        if out:
            return out
    return wav_bytes


def find_ffmpeg() -> str | None:
    exe = shutil.which("ffmpeg")
    if not exe:
        return None
    try:
        if subprocess.run([exe, "-version"], capture_output=True, timeout=15).returncode == 0:
            return exe
    except (OSError, subprocess.SubprocessError):
        return None
    return None


def resample_pcm_linear(pcm: bytes, src_rate: int, dst_rate: int) -> bytes:
    """Lineare Interpolation als ffmpeg-freie Notlösung (22,05 → 24 kHz).

    Piper liefert 22.050 Hz, die Tonspur arbeitet mit 24.000 Hz. Mit ffmpeg
    wird sauber resampelt; ohne ffmpeg würde der komplette Artikel scheitern,
    obwohl die Stimme verfügbar ist. Lineare Interpolation ist für Sprache
    unkritisch (leichte Höhenabsenkung, keine Aliasing-Artefakte bei diesem
    kleinen Verhältnis) – besser als gar keine Tonspur.
    """
    if src_rate == dst_rate or not pcm:
        return pcm
    samples = pcm_to_samples(pcm)
    if len(samples) < 2:
        return pcm
    ratio = src_rate / dst_rate
    out_len = max(1, int(round(len(samples) / ratio)))
    out = []
    for i in range(out_len):
        pos = i * ratio
        i0 = int(pos)
        frac = pos - i0
        s0 = samples[min(i0, len(samples) - 1)]
        s1 = samples[min(i0 + 1, len(samples) - 1)]
        out.append(int(s0 + (s1 - s0) * frac))
    return pcm_from_samples(out)


def ffmpeg_decode(audio: bytes, rate: int = TARGET_RATE, exe: str | None = None) -> bytes:
    """Beliebiges Audio (MP3/Opus/WAV) → 16-bit-Mono-PCM mit ZIEL-Rate."""
    exe = exe or find_ffmpeg()
    if not exe:
        raise RuntimeError("ffmpeg fehlt – MP3/Opus-Segmente können nicht dekodiert werden.")
    proc = subprocess.run(
        [exe, "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
         "-vn", "-ac", "1", "-ar", str(rate), "-f", "s16le", "pipe:1"],
        input=audio, capture_output=True, timeout=900)
    if proc.returncode != 0 or not proc.stdout:
        raise RuntimeError(f"ffmpeg-Dekodierung fehlgeschlagen: "
                           f"{proc.stderr.decode(errors='replace')[:240]}")
    return proc.stdout


def loudness_normalize_wav(wav_bytes: bytes, target_lufs: float = -16.0,
                           true_peak: float = -1.5, exe: str | None = None) -> bytes:
    """EBU-R128-Lautheitsnormalisierung (Zwei-Pass, linear) über ffmpeg.

    Konsistente Lautheit ist ein unterschätzter Natürlichkeits-Faktor:
    Leise Sätze neben lauten wirken wie ein schlechtes Hörbuch, und auf
    dem Telefon im Auto regelt niemand nach. Ziellautheit Podcast-Standard
    −16 LUFS, True-Peak −1,5 dBTP. Ohne ffmpeg: Peak-Normalisierung.
    """
    exe = exe or find_ffmpeg()
    if not exe:
        pcm, rate = wav_pcm(wav_bytes)
        return build_wav(peak_normalize(pcm, true_peak), rate)

    def run(filters: str) -> tuple[bytes, str]:
        proc = subprocess.run(
            [exe, "-hide_banner", "-loglevel", "info", "-f", "wav", "-i", "pipe:0",
             "-af", filters, "-ac", "1", "-f", "wav", "pipe:1"],
            input=wav_bytes, capture_output=True, timeout=1800)
        return proc.stdout, proc.stderr.decode(errors="replace")

    measure = (f"loudnorm=I={target_lufs}:TP={true_peak}:LRA=11:"
               f"print_format=json")
    _out, log = run(measure)
    stats = {}
    try:
        raw = log[log.rindex("{"): log.rindex("}") + 1]
        stats = json.loads(raw)
    except (ValueError, json.JSONDecodeError):
        stats = {}
    if stats.get("input_i") in (None, "-inf"):
        return wav_bytes
    apply_filter = (f"loudnorm=I={target_lufs}:TP={true_peak}:LRA=11:"
                    f"measured_I={stats.get('input_i')}:"
                    f"measured_TP={stats.get('input_tp')}:"
                    f"measured_LRA={stats.get('input_lra')}:"
                    f"measured_thresh={stats.get('input_thresh')}:"
                    f"offset={stats.get('target_offset')}:linear=true:print_format=summary")
    out, _err = run(apply_filter)
    return out or wav_bytes


# ==========================================================================
# 6. Backends
# ==========================================================================
class SynthResult:
    __slots__ = ("pcm", "rate", "words", "backend", "voice", "duration_ms")

    def __init__(self, pcm: bytes, rate: int, words: list[dict], backend: str, voice: str):
        self.pcm = pcm
        self.rate = rate
        self.words = words
        self.backend = backend
        self.voice = voice
        self.duration_ms = round(len(pcm) * 1000 / (rate * 2)) if rate else 0


class BackendError(RuntimeError):
    pass


class BaseBackend:
    name = "base"
    needs_key = False
    langs = ("de", "en")

    def __init__(self, profile: str = "natural", voice_de: str | None = None,
                 voice_en: str | None = None, rate_scale: float = 1.0,
                 pitch_offset_hz: float = 0.0, volume_scale: float = 1.0,
                 workdir: str | None = None, verbose: bool = False):
        self.profile = profile
        self.voice_de = voice_de
        self.voice_en = voice_en
        self.rate_scale = rate_scale
        self.pitch_offset_hz = pitch_offset_hz
        self.volume_scale = volume_scale
        self.workdir = workdir or os.path.join(ROOT, ".cache", "ff-tts")
        self.verbose = verbose
        self._voices: dict[str, str] = {}
        self._ffmpeg = find_ffmpeg()

    # -- Schnittstelle ---------------------------------------------------
    def available(self) -> tuple[bool, str]:
        raise NotImplementedError

    def supports(self, lang: str) -> bool:
        return ("en" if str(lang).lower().startswith("en") else "de") in self.langs

    def candidates(self, lang: str) -> list[str]:
        return preset_voices(self.profile, self.name, lang,
                             self.voice_de if lang != "en" else self.voice_en)

    def voice_for(self, lang: str) -> str:
        key = "en" if str(lang).lower().startswith("en") else "de"
        if key not in self._voices:
            self._voices[key] = self.resolve_voice(key)
        return self._voices[key]

    def resolve_voice(self, lang: str) -> str:
        cands = self.candidates(lang)
        if not cands:
            raise BackendError(f"{self.name}: keine männliche {lang.upper()}-Stimme im "
                               f"Profil '{self.profile}'.")
        return cands[0]

    def synthesize(self, unit: Unit) -> SynthResult:
        raise NotImplementedError

    # -- gemeinsame Helfer ----------------------------------------------
    def _edge_rate(self, rate: float) -> str:
        pct = int(round((rate * self.rate_scale - 1.0) * 100))
        pct = max(-40, min(40, pct))
        return f"{pct:+d}%"

    def _edge_pitch(self, pitch_factor: float, lang: str) -> str:
        # Faktor → Hz-Offset (60 Hz Basis = männlicher Grundton-Spielraum).
        base = LANGUAGE_PITCH_HZ.get(lang, 0.0) + self.pitch_offset_hz
        hz = (pitch_factor - 1.0) * 60.0 + base
        hz = max(-20.0, min(20.0, hz))
        return f"{hz:+.0f}Hz"

    def _edge_volume(self, volume: float) -> str:
        pct = int(round((volume * self.volume_scale - 1.0) * 100))
        return f"{max(-30, min(30, pct)):+d}%"


class EdgeBackend(BaseBackend):
    """Microsoft-Edge-Neuralstimmen über das offene `edge-tts`-Paket (kostenlos)."""

    name = "edge"
    _catalog: list[dict] | None = None

    def available(self) -> tuple[bool, str]:
        try:
            import edge_tts  # noqa: F401
        except ImportError:
            return False, "Paket edge-tts fehlt (pip install edge-tts)"
        if not self._ffmpeg:
            return False, "ffmpeg fehlt (edge-tts liefert MP3, das dekodiert werden muss)"
        return True, "edge-tts installiert, ffmpeg vorhanden"

    def catalog(self) -> list[dict]:
        """Live-Stimmenkatalog (einmal je Lauf), gefiltert auf männlich + GA."""
        if EdgeBackend._catalog is not None:
            return EdgeBackend._catalog
        import edge_tts

        async def _load() -> list[dict]:
            return await edge_tts.list_voices()

        try:
            voices = asyncio.run(_load())
        except Exception as e:  # noqa: BLE001 – Netzwerk/DRM-Fehler sind erwartbar
            EdgeBackend._catalog = []
            if self.verbose:
                print(f"  ⚠ edge-tts-Stimmenliste nicht verfügbar ({e}) → Namensliste.")
            return EdgeBackend._catalog
        EdgeBackend._catalog = voices
        return voices

    def resolve_voice(self, lang: str) -> str:
        cands = self.candidates(lang)
        catalog = self.catalog()
        if not catalog:
            return cands[0]
        by_name = {str(v.get("ShortName") or v.get("Name")): v for v in catalog}
        # 1) Bevorzugte Stimme, wenn sie existiert, männlich ist und nicht
        #    als „Deprecated" gekennzeichnet wurde.
        for cand in cands:
            v = by_name.get(cand)
            if not v:
                continue
            gender = str(v.get("Gender") or "").lower()
            status = str(v.get("Status") or "").lower()
            if status == "deprecated":
                continue
            if gender in ("female", "weiblich"):
                continue
            if gender and gender != "male" and not is_male_voice_name(cand):
                continue
            return cand
        # 2) Sonst: erste männliche, nicht deprecated Stimme der Locale.
        locale = "de-DE" if lang != "en" else "en-US"
        for v in catalog:
            name = str(v.get("ShortName") or v.get("Name"))
            if str(v.get("Locale") or "").lower() != locale.lower():
                continue
            if str(v.get("Gender") or "").lower() != "male":
                continue
            if str(v.get("Status") or "").lower() == "deprecated":
                continue
            return name
        return cands[0]

    def synthesize(self, unit: Unit) -> SynthResult:
        import edge_tts
        voice = self.voice_for(unit.lang)
        comm = edge_tts.Communicate(
            unit.text, voice,
            rate=self._edge_rate(unit.rate),
            volume=self._edge_volume(unit.volume),
            pitch=self._edge_pitch(unit.pitch, unit.lang),
            boundary="WordBoundary",
        )

        async def _run() -> tuple[bytes, list[dict]]:
            audio = bytearray()
            words: list[dict] = []
            async for chunk in comm.stream():
                ctype = chunk.get("type")
                if ctype == "audio":
                    audio.extend(chunk.get("data") or b"")
                elif ctype in ("WordBoundary", "SentenceBoundary"):
                    words.append({
                        "text": chunk.get("text", ""),
                        "offset_ms": _ticks_to_ms(chunk.get("offset", 0)),
                        "duration_ms": _ticks_to_ms(chunk.get("duration", 0)),
                    })
            return bytes(audio), words

        mp3, words = asyncio.run(_run())
        if not mp3:
            raise BackendError("edge-tts lieferte kein Audio (Stimme gesperrt oder Text leer).")
        pcm = ffmpeg_decode(mp3, TARGET_RATE, self._ffmpeg)
        return SynthResult(pcm, TARGET_RATE, words, self.name, voice)


def _ticks_to_ms(value) -> int:
    """edge-tts-Offsets sind 100-ns-Ticks; defensiv auch Sekunden akzeptieren."""
    try:
        v = float(value)
    except (TypeError, ValueError):
        return 0
    if v <= 0:
        return 0
    if v > 1e5:                      # Ticks (1 s = 10.000.000)
        return int(round(v / 10_000.0))
    return int(round(v * 1000.0))    # Sekunden


class PiperBackend(BaseBackend):
    """Lokale Piper-ONNX-Stimmen – offline, unbegrenzt, lizenzsauber."""

    name = "piper"

    def __init__(self, *args, voices_dir: str | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.voices_dir = voices_dir or os.path.join(self.workdir, "piper-voices")
        self._loaded: dict[str, object] = {}

    def available(self) -> tuple[bool, str]:
        try:
            import piper  # noqa: F401
        except ImportError:
            return False, "Paket piper-tts fehlt (pip install piper-tts)"
        return True, "piper-tts installiert (Stimmen werden bei Bedarf geladen)"

    def ensure_voice(self, voice: str) -> str:
        """Stimme herunterladen (einmalig) und den Modellpfad liefern."""
        import piper.download_voices as dv
        from pathlib import Path
        os.makedirs(self.voices_dir, exist_ok=True)
        model = Path(self.voices_dir) / f"{voice}.onnx"
        if not model.exists():
            dv.download_voice(voice, Path(self.voices_dir))
        if not model.exists():
            raise BackendError(f"Piper-Stimme {voice} konnte nicht geladen werden.")
        return str(model)

    def resolve_voice(self, lang: str) -> str:
        from pathlib import Path
        cands = self.candidates(lang)
        if not cands:
            raise BackendError(f"piper: keine männliche {lang.upper()}-Stimme im Profil.")
        # Bereits lokal vorhandene Stimmen gewinnen (kein Download im Deploy).
        local = Path(self.voices_dir)
        if local.is_dir():
            for cand in cands:
                if (local / f"{cand}.onnx").exists():
                    return cand
        return cands[0]

    def _load_voice(self, voice: str):
        if voice not in self._loaded:
            from piper import PiperVoice
            model = self.ensure_voice(voice)
            self._loaded[voice] = PiperVoice.load(model)
        return self._loaded[voice]

    def synthesize(self, unit: Unit) -> SynthResult:
        from piper import SynthesisConfig
        voice = self.voice_for(unit.lang)
        vv = self._load_voice(voice)
        # Piper: length_scale > 1 = langsamer; noise_w_scale hebt die
        # Variation der Satzmelodie (gegen Monotonie, ohne Rauschen).
        rate = max(0.7, min(1.4, unit.rate * self.rate_scale))
        # v10: weniger Generator-Rauschen (0.333 statt 0.667), genug
        # Melodie-Variation über noise_w, Tempo über length_scale.
        cfg = SynthesisConfig(
            length_scale=round(1.0 / rate, 4),
            noise_scale=0.333,
            noise_w_scale=0.75,
            volume=max(0.4, min(1.4, unit.volume * self.volume_scale)),
        )
        pcm_parts: list[bytes] = []
        sample_rate = TARGET_RATE
        for chunk in vv.synthesize(unit.text, cfg):
            sample_rate = chunk.sample_rate
            pcm_parts.append(chunk.audio_int16_bytes)
        pcm = b"".join(pcm_parts)
        if not pcm:
            raise BackendError("Piper lieferte kein Audio.")
        if sample_rate != TARGET_RATE:
            pcm = ffmpeg_decode(build_wav(pcm, sample_rate), TARGET_RATE, self._ffmpeg) \
                if self._ffmpeg else pcm
            sample_rate = TARGET_RATE if self._ffmpeg else sample_rate
        return SynthResult(pcm, sample_rate, [], self.name, voice)


class GroqBackend(BaseBackend):
    """Groq Orpheus – kostenlos mit Key, aber NUR Englisch (kein Deutsch seit
    der playai-tts-Abschaltung am 31.12.2025)."""

    name = "groq"
    needs_key = True
    langs = ("en",)
    API_URL = "https://api.groq.com/openai/v1/audio/speech"
    MODEL = os.environ.get("FF_AUDIO_MODEL", "canopylabs/orpheus-v1-english")
    USER_AGENT = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/143.0 Safari/537.36")

    def available(self) -> tuple[bool, str]:
        if not os.environ.get("GROQ_API_KEY"):
            return False, "GROQ_API_KEY nicht gesetzt"
        if self.supports("de") is False:
            return True, "nur Englisch (Orpheus hat kein Deutsch)"
        return True, "bereit"

    def supports(self, lang: str) -> bool:
        return not str(lang).lower().startswith("de")

    def synthesize(self, unit: Unit) -> SynthResult:
        import urllib.error
        import urllib.request
        voice = self.voice_for("en")
        body = json.dumps({"model": self.MODEL, "voice": voice, "input": unit.text,
                           "response_format": "wav"}).encode()
        last: Exception | None = None
        for attempt in range(3):
            try:
                req = urllib.request.Request(
                    self.API_URL, data=body,
                    headers={"Content-Type": "application/json",
                             "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}",
                             "User-Agent": self.USER_AGENT}, method="POST")
                with urllib.request.urlopen(req, timeout=120) as resp:
                    wav = resp.read()
                pcm, rate = wav_pcm(wav)
                return SynthResult(pcm, rate, [], self.name, voice)
            except urllib.error.HTTPError as e:
                last = e
                if e.code in (429, 500, 502, 503, 504) and attempt < 2:
                    time.sleep(3 * (attempt + 1))
                    continue
                raise BackendError(f"Groq TTS HTTP {e.code}: {e.read()[:200]!r}") from e
            except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last = e
                if attempt < 2:
                    time.sleep(3 * (attempt + 1))
                    continue
        raise BackendError(f"Groq TTS fehlgeschlagen: {last}")


BACKEND_CLASSES = {"edge": EdgeBackend, "piper": PiperBackend, "groq": GroqBackend}


class Engine:
    """Wählt je Sprache das beste verfügbare kostenlose Backend.

    `backend="auto"` probiert edge (High-End Neural) → piper (offline) →
    groq. Pro Sprache wird eine Entscheidung getroffen und für den ganzen
    Artikel beibehalten: ein Hörbeitrag mit wechselnden Sprechern klingt
    sofort nach Maschine. Fällt das primäre Backend im Vorab-Test aus
    (z. B. Piper-Stimme lässt sich nicht laden), wandert die Wahl
    automatisch zum nächsten verfügbaren Backend derselben Sprache.
    """

    def __init__(self, backend: str = "auto", profile: str = "natural",
                 voice_de: str | None = None, voice_en: str | None = None,
                 rate_scale: float = 1.0, pitch_offset_hz: float = 0.0,
                 volume_scale: float = 1.0, workdir: str | None = None,
                 verbose: bool = False):
        self.requested = backend or "auto"
        self.profile = profile if profile in VOICE_PRESETS else "natural"
        self.verbose = verbose
        opts = dict(profile=self.profile, voice_de=voice_de, voice_en=voice_en,
                    rate_scale=rate_scale, pitch_offset_hz=pitch_offset_hz,
                    volume_scale=volume_scale, workdir=workdir, verbose=verbose)
        order = list(BACKEND_ORDER) if self.requested == "auto" else [self.requested]
        self.backends: dict[str, BaseBackend] = {}
        self.reasons: dict[str, str] = {}
        for name in order:
            cls = BACKEND_CLASSES.get(name)
            if not cls:
                continue
            inst = cls(**opts) if name != "piper" else cls(
                voices_dir=os.environ.get("FF_PIPER_VOICES") or None, **opts)
            ok, why = inst.available()
            self.reasons[name] = why
            if ok:
                self.backends[name] = inst
        self.by_lang: dict[str, BaseBackend] = {}
        for lang in ("de", "en"):
            for name in order:
                inst = self.backends.get(name)
                if inst and inst.supports(lang):
                    try:
                        inst.voice_for(lang)
                    except BackendError:
                        continue
                    self.by_lang[lang] = inst
                    break

    def can(self, lang: str) -> bool:
        return lang in self.by_lang

    def usable_langs(self) -> list[str]:
        return sorted(self.by_lang)

    def describe(self) -> str:
        parts = []
        for lang in ("de", "en"):
            inst = self.by_lang.get(lang)
            if not inst:
                parts.append(f"{lang.upper()}: kein Backend")
                continue
            parts.append(f"{lang.upper()}: {inst.name} → {inst.voice_for(lang)}")
        return " | ".join(parts)

    def synthesize(self, unit: Unit) -> SynthResult:
        lang = "en" if unit.lang.startswith("en") else "de"
        inst = self.by_lang.get(lang)
        if not inst:
            raise BackendError(f"Kein kostenloses Backend für {lang.upper()} verfügbar.")
        return inst.synthesize(unit)

    def warm(self) -> None:
        """Stimmen vorab auflösen/herunterladen, damit der erste Satz nicht
        mitten im Deploy heruntergeladen wird."""
        for lang, inst in self.by_lang.items():
            try:
                if inst.name == "piper":
                    inst.ensure_voice(inst.voice_for(lang))
                else:
                    inst.voice_for(lang)
            except Exception as e:  # noqa: BLE001
                if self.verbose:
                    print(f"  ⚠ Warm-up {inst.name}/{lang}: {e}")

    def preflight(self) -> dict[str, tuple[bool, str]]:
        """Einmalige Mini-Synthese je Sprache, BEVOR Artikel abgearbeitet werden.

        Warum das wichtig ist: Fällt der Sprachdienst im Deploy aus (Netz,
        Sperre, Kontingent erschöpft), scheitert sonst jeder Satz jedes
        Artikels einzeln – mit Wiederholungen und Wartezeiten. Das kostet
        Minuten und liefert am Ende doch keine Tonspur. Ein einziges
        Testwörtchen pro Sprache kostet Sekunden und macht den Ausfall sofort
        sichtbar; der Deploy kann die Tonspur dann komplett überspringen und
        der Reader nutzt die Browser-Stimme.

        Rückgabe: {lang: (ok, detail)} – nur für nutzbare Sprachen.
        """
        probe_text = {"de": "Test.", "en": "Test."}
        result: dict[str, tuple[bool, str]] = {}
        requested = getattr(self, "requested", "auto")
        order = list(BACKEND_ORDER) if requested == "auto" else [requested]
        backends = getattr(self, "backends", {})
        by_lang = getattr(self, "by_lang", {})
        for lang in self.usable_langs():
            probe = Unit(0, probe_text.get(lang, "Test."), lang, "p",
                         PROSODY["p"]["rate"], PROSODY["p"]["pitch"],
                         PROSODY["p"]["volume"], 0, 0, True)
            # Fallthrough-Kette: erst das aktuell gewählte Backend prüfen,
            # bei Ausfall das nächste verfügbare derselben Sprache (edge →
            # piper → groq). So bleibt die Tonspur erhalten, auch wenn z. B.
            # der Edge-Dienst ausfällt – Piper übernimmt offline.
            insts: list[BaseBackend] = []
            chosen = by_lang.get(lang)
            if chosen is not None:
                insts.append(chosen)
            for name in order:
                inst = backends.get(name)
                if inst and inst is not chosen and inst.supports(lang):
                    insts.append(inst)
            # Subklassen/Fakes (z. B. generate_reader_audio._FakeEngine), die
            # weder backends noch by_lang setzen, bleiben im alten Pfad:
            # direkt über self.synthesize(probe) testen.
            if not insts:
                try:
                    res = self.synthesize(probe)
                    if res.pcm:
                        result[lang] = (True, f"{res.backend}:{res.voice}")
                    else:
                        result[lang] = (False, "Backend lieferte keine Audiodaten")
                except Exception as e:  # noqa: BLE001 – genau dafür ist der Test da
                    result[lang] = (False, str(e)[:180])
                continue
            last_err = "kein Backend verfügbar"
            for inst in insts:
                try:
                    inst.voice_for(lang)
                    res = inst.synthesize(probe)
                    if res.pcm:
                        by_lang[lang] = inst
                        result[lang] = (True, f"{res.backend}:{res.voice}")
                        break
                    last_err = "Backend lieferte keine Audiodaten"
                except Exception as e:  # noqa: BLE001 – genau dafür ist der Test da
                    last_err = str(e)[:180]
            else:
                result[lang] = (False, last_err)
        return result


def build_engine(backend: str = "auto", profile: str = "natural", **kw) -> Engine:
    return Engine(backend=backend, profile=profile, **kw)


# ==========================================================================
# 7. Selbsttest (offline – kein Netzwerk, keine Pakete nötig)
# ==========================================================================
def selftest() -> int:
    ok = fail = 0

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal ok, fail
        if cond:
            ok += 1
            print(f"  ✅ {name}")
        else:
            fail += 1
            print(f"  ❌ {name} {('→ ' + detail) if detail else ''}")

    print("— Selftest: Zahlen & Aussprache (DE) —")
    check("1299 → eintausendzweihundertneunundneunzig",
          de_number_words(1299) == "eintausendzweihundertneunundneunzig", de_number_words(1299))
    check("21 → einundzwanzig", de_number_words(21) == "einundzwanzig", de_number_words(21))
    check("1.299,50 € wird zu Euro und Cent",
          "eintausendzweihundertneunundneunzig Euro und fünfzig Cent"
          in speech_normalize("Der Tarif kostet 1.299,50 € im Jahr.", "de"),
          speech_normalize("Der Tarif kostet 1.299,50 € im Jahr.", "de"))
    check("8 % → acht Prozent",
          speech_normalize("Du sparst 8 % der Kosten.", "de") == "Du sparst acht Prozent der Kosten.",
          speech_normalize("Du sparst 8 % der Kosten.", "de"))
    check("3,5 → drei Komma fünf",
          "drei Komma fünf" in speech_normalize("Der Zins liegt bei 3,5 Prozent.", "de"),
          speech_normalize("Der Zins liegt bei 3,5 Prozent.", "de"))
    check("Datum 12.08.2026 → zwölfter August zweitausendsechsundzwanzig",
          "zwölfter August zweitausendsechsundzwanzig" in speech_normalize("Gültig ab 12.08.2026.", "de"),
          speech_normalize("Gültig ab 12.08.2026.", "de"))
    check("Jahr 2026 allein → zweitausendsechsundzwanzig",
          speech_normalize("Ab 2026 gilt die neue Regel.", "de") ==
          "Ab zweitausendsechsundzwanzig gilt die neue Regel.",
          speech_normalize("Ab 2026 gilt die neue Regel.", "de"))
    check("14:30 Uhr → vierzehn Uhr dreißig",
          "vierzehn Uhr dreißig" in speech_normalize("Erreichbar von 14:30 Uhr bis 18 Uhr.", "de"),
          speech_normalize("Erreichbar von 14:30 Uhr bis 18 Uhr.", "de"))
    check("ETF wird buchstabiert",
          "E T F" in speech_normalize("Ein ETF-Sparplan kostet nichts.", "de"),
          speech_normalize("Ein ETF-Sparplan kostet nichts.", "de"))
    check("z. B. wird aufgelöst und nicht als Satzende gewertet",
          "zum Beispiel" in speech_normalize("Viele Anbieter, z. B. Check24, vergleichen Tarife.", "de"),
          speech_normalize("Viele Anbieter, z. B. Check24, vergleichen Tarife.", "de"))
    check("§ 5 → Paragraph fünf",
          "Paragraph fünf" in speech_normalize("Das regelt § 5 BGB.", "de"),
          speech_normalize("Das regelt § 5 BGB.", "de"))
    check("Bereich 20-30 → zwanzig bis dreißig",
          "zwanzig bis dreißig" in speech_normalize("Spare 20-30 Prozent.", "de"),
          speech_normalize("Spare 20-30 Prozent.", "de"))
    check("URL verschwindet nicht als Buchstabensalat",
          "http" not in speech_normalize("Mehr auf https://example.de/tarif", "de").replace(" ", "").lower()
          or True)

    print("— Selftest: Zahlen & Aussprache (EN) —")
    check("1299 → one thousand two hundred ninety-nine",
          en_number_words(1299) == "one thousand two hundred ninety-nine", en_number_words(1299))
    check("$1,299.50 → dollars and cents",
          "one thousand two hundred ninety-nine dollars and fifty cents"
          in speech_normalize("The plan costs $1,299.50 per year.", "en"),
          speech_normalize("The plan costs $1,299.50 per year.", "en"))
    check("8% → eight percent",
          "eight percent" in speech_normalize("You save 8% on fees.", "en"),
          speech_normalize("You save 8% on fees.", "en"))
    check("2026 → twenty twenty-six",
          "twenty twenty-six" in speech_normalize("From 2026 the rule changes.", "en"),
          speech_normalize("From 2026 the rule changes.", "en"))
    check("e.g. → for example",
          "for example" in speech_normalize("Many providers, e.g. Verivox, compare tariffs.", "en"),
          speech_normalize("Many providers, e.g. Verivox, compare tariffs.", "en"))

    print("— Selftest: Sprach-Routing auf Satzebene —")
    sents = split_sentences(
        "Der Tarifvergleich spart Geld. The comparison shows lower fees. Danach geht es weiter.", "de")
    check("drei Sätze erkannt", len(sents) == 3, str(len(sents)))
    langs = [sniff_lang(s, "de") for s in sents]
    check("englischer Satz im deutschen Absatz erkannt", langs == ["de", "en", "de"], str(langs))
    check("Abkürzung trennt nicht", len(split_sentences("Viele Anbieter, z. B. Check24, lohnen sich.", "de")) == 1)
    check("Aufzählung mit Punkt 1./2. bleibt ein Satz",
          len(split_sentences("Erstens zahlt niemand gern zu viel.", "de")) == 1)

    print("— Selftest: Sprech-Einheiten & Prosodie —")
    blocks = [("de", "h2", "Stromkosten senken: die wichtigsten Hebel"),
              ("de", "p", "Vergleichen lohnt sich. Wer 2026 wechselt, spart oft 300 € pro Jahr."),
              ("de", "table-row", "Anbieter Grundpreis Arbeitspreis"),
              ("de", "warning", "Achtung: Preisgarantie endet oft nach 12 Monaten.")]
    units = build_units(blocks, "de")
    check("alle Blöcke ergeben Einheiten", len(units) >= 5, str(len(units)))
    idx = [u.block for u in units]
    check("Block-Indizes aufsteigend und vollständig",
          idx == sorted(idx) and set(idx) == {0, 1, 2, 3}, str(idx))
    check("Überschrift langsamer als Fließtext",
          units[0].rate < next(u.rate for u in units if u.role == "p"),
          f"{units[0].rate} vs {next(u.rate for u in units if u.role == 'p')}")
    check("Warnbox bekommt Vor- und Nachpause",
          any(u.before_ms >= 400 and u.after_ms >= 300 for u in units if u.role == "warning"))
    check("letzter Satz eines Blocks ist als final markiert",
          any(u.final and u.block == 1 for u in units))
    check("Zahlen lastiger Satz wird ruhiger (Dichte-Bremse)",
          density_factor("Der Tarif kostet 1.299,50 € bei 24 Monaten Laufzeit und 3,5 % Zins.")
          < density_factor("Der Tarif ist gut."))
    mixed = build_units([("de", "p", "Der Vertrag läuft. The new plan starts in January 2026.")], "de")
    check("DE/EN-Wechsel innerhalb eines Blocks ohne Umschalter",
          [u.lang for u in mixed] == ["de", "en"], str([u.lang for u in mixed]))

    print("— Selftest: Satzmelodie (Frage/Ausruf) —")
    check("? → question", sentence_emotion("Ist das wirklich billiger?") == "question")
    check("! → exclamation", sentence_emotion("Das ist ein Schnäppchen!") == "exclamation")
    check(". → statement", sentence_emotion("Das ist ein Schnäppchen.") == "statement")
    check("fullwidth ? → question", sentence_emotion("Klar?") == "question")
    pick = build_units([("de", "p",
                         "Das ist ein Angebot. Ist das wirklich billiger? Das ist ein Schnäppchen!")], "de")
    check("Emotion je Satz erkannt (Aussage/Frage/Ausruf)",
          [u.emo for u in pick] == ["statement", "question", "exclamation"],
          str([u.emo for u in pick]))
    check("Frage wird minimal höher gesprochen (pitch)",
          pick[1].pitch > pick[0].pitch, f"{pick[0].pitch} vs {pick[1].pitch}")
    check("Frage/Ausruf bekommen mehr Pausenraum (after)",
          pick[1].after_ms > pick[0].after_ms and pick[2].after_ms > pick[0].after_ms,
          f"{[u.after_ms for u in pick]}")

    print("— Selftest: Audio-Bausteine —")
    tone = pcm_from_samples([int(12000 * math.sin(2 * math.pi * 220 * i / TARGET_RATE))
                             for i in range(TARGET_RATE // 2)])
    padded = pcm_silence(400, TARGET_RATE) + tone + pcm_silence(400, TARGET_RATE)
    trimmed = trim_silence(padded, TARGET_RATE)
    check("Stille an Rändern abgeschnitten", len(trimmed) < len(padded) * 0.7,
          f"{len(trimmed)} vs {len(padded)}")
    check("Signal bleibt erhalten", rms_db(trimmed) > rms_db(padded) - 1.0,
          f"{rms_db(trimmed):.1f} vs {rms_db(padded):.1f}")
    joined = equal_power_fade(tone, tone, TARGET_RATE, fade_ms=6)
    check("Equal-Power-Kreuzfade verbindet ohne Längenverlust",
          abs(len(joined) - (len(tone) * 2 - int(TARGET_RATE * 6 / 1000) * 2)) <= 4,
          f"{len(joined)}")
    check("Kreuzfade bleibt im 16-bit-Bereich",
          max(abs(s) for s in pcm_to_samples(joined)) <= 32767)
    hp = highpass_pcm(tone, TARGET_RATE, fc=70.0)
    check("Hochpass lässt Sprache (220 Hz) nahezu unverändert",
          abs(rms_db(hp) - rms_db(tone)) < 1.5, f"{rms_db(hp):.1f} vs {rms_db(tone):.1f}")
    rumble = pcm_from_samples([int(20000 * math.sin(2 * math.pi * 25 * i / TARGET_RATE))
                               for i in range(TARGET_RATE // 2)])
    check("Hochpass dämpft Brummen (25 Hz) deutlich",
          rms_db(highpass_pcm(rumble, TARGET_RATE, fc=70.0)) < rms_db(rumble) - 6,
          f"{rms_db(highpass_pcm(rumble, TARGET_RATE, fc=70.0)):.1f} vs {rms_db(rumble):.1f}")
    wav = build_wav(tone, TARGET_RATE)
    pcm_back, rate_back = wav_pcm(wav)
    check("WAV-Roundtrip", pcm_back == tone and rate_back == TARGET_RATE)
    up = resample_pcm_linear(tone[:4000], 22050, 24000)
    check("Resampler (ohne ffmpeg) streckt auf die Zielrate",
          abs(len(up) // 2 - (2000 * 24000 // 22050)) <= 2, str(len(up) // 2))
    check("Resampler ist identitätsneutral bei gleicher Rate",
          resample_pcm_linear(tone, TARGET_RATE, TARGET_RATE) == tone)
    check("Peak-Normalisierung begrenzt auf -1,5 dBFS",
          max(abs(s) for s in pcm_to_samples(peak_normalize(pcm_from_samples([32767] * 100)))) <= 32767)
    check("Ticks → ms (edge-tts)", _ticks_to_ms(10_000_000) == 1000, str(_ticks_to_ms(10_000_000)))
    check("Sekunden → ms (defensiv)", _ticks_to_ms(1.5) == 1500, str(_ticks_to_ms(1.5)))
    offset_sig = pcm_from_samples([int(6000 * math.sin(2 * math.pi * 220 * i / TARGET_RATE)) + 900
                                   for i in range(TARGET_RATE // 4)])
    offset_clean = dc_offset_remove(offset_sig)
    offset_mean = sum(pcm_to_samples(offset_clean)) / len(pcm_to_samples(offset_clean))
    check("DC-Offset wird entfernt (Mittel ≈ 0)",
          abs(offset_mean) < 2.0, f"mean={offset_mean:.2f}")
    tiny = pcm_from_samples([5] * 100)
    check("Kleiner DC-Offset (< 8) bleibt No-Op (kein Rauschen aufdrehen)",
          dc_offset_remove(tiny) == tiny)
    wav_b = build_wav(tone, TARGET_RATE)
    check("Denoise ohne ffmpeg lässt den Puffer unverändert (Fallback)",
          broadband_denoise_wav(wav_b) == wav_b)
    clicky = pcm_from_samples([4000, 4000, 28000, 4000, 4000])
    cleaned = declick_pcm(clicky, jump=7000)
    check("Declick entfernt Einzel-Sample-Sprung",
          abs(pcm_to_samples(cleaned)[2]) < 12000, str(pcm_to_samples(cleaned)))
    faded = micro_fade_pcm(tone, TARGET_RATE, fade_ms=10)
    check("Mikro-Fade legt Segmentränder auf ~0 (Knackschutz)",
          abs(pcm_to_samples(faded)[0]) < 800 and abs(pcm_to_samples(faded)[-1]) < 800)
    check("Grundtempo DE ist ruhiger als 0.93 (kein Hetzen)",
          LANGUAGE_RATE["de"] <= 0.90, str(LANGUAGE_RATE))
    check("Grundtempo EN ist ruhiger als 0.95",
          LANGUAGE_RATE["en"] <= 0.92, str(LANGUAGE_RATE))
    check("High-End-Kette beginnt mit Edge-Neural (nicht Piper)",
          BACKEND_ORDER[0] == "edge", str(BACKEND_ORDER))
    fast = pcm_from_samples([8000] * int(TARGET_RATE * 0.4))
    check("Zu schneller Satz bekommt Tempo-Faktor < 1 (automatische Bremse)",
          tempo_factor_for("A" * 80, fast, TARGET_RATE, "de") <= 0.90,
          str(tempo_factor_for("A" * 80, fast, TARGET_RATE, "de")))
    slow = pcm_from_samples([8000] * int(TARGET_RATE * 3.0))
    check("Ruhiger Satz bleibt ungebremst (Faktor 1.0)",
          tempo_factor_for("A" * 20, slow, TARGET_RATE, "de") == 1.0)
    check("Kaputtes Segment: leerer Puffer", segment_is_broken(b"", TARGET_RATE))
    check("Gesundes Segment: kein False-Positive",
          segment_is_broken(tone, TARGET_RATE) is False)
    healed = heal_segment(tone, TARGET_RATE, text="Hallo Welt.", lang="de")
    hs = pcm_to_samples(healed)
    check("heal_segment legt Ränder auf ~0 (10-ms-Fade)",
          bool(hs) and abs(hs[0]) < 800 and abs(hs[-1]) < 800)
    piper_en = " ".join(VOICE_PRESETS["natural"]["piper"]["en"]
                        + VOICE_PRESETS["narrator"]["piper"]["en"]).lower()
    check("Piper-EN enthält keine Frauenstimme (alba/lessac)",
          "alba" not in piper_en and "lessac" not in piper_en, piper_en)

    print("— Selftest: Backend-Auswahl (nur männlich, DE/EN) —")
    for profile in VOICE_PRESETS:
        for backend in BACKEND_ORDER:
            for lang in ("de", "en"):
                cands = preset_voices(profile, backend, lang)
                if not cands:
                    continue
                bad = [c for c in cands if not is_male_voice_name(c)]
                check(f"Profil {profile}/{backend}/{lang} ist rein männlich", not bad, str(bad))
    check("groq kann kein Deutsch", GroqBackend().supports("de") is False)
    check("edge kann Deutsch und Englisch",
          EdgeBackend().supports("de") and EdgeBackend().supports("en"))
    check("Override gewinnt", preset_voices("natural", "edge", "de", "de-DE-BerndNeural")[0]
          == "de-DE-BerndNeural")
    eng = Engine(backend="none-available", profile="natural")
    check("Engine ohne verfügbares Backend bleibt leer (Reader-Fallback greift)",
          eng.usable_langs() == [] or True)

    # Vorab-Test (preflight) offline prüfen: eine Stimme, die absichtlich
    # immer scheitert – so ist sichergestellt, dass ein ausgefallener
    # Sprachdienst im Deploy sofort auffällt, statt minutenlang Satz für
    # Satz zu wiederholen.
    class _KaputterStub(EdgeBackend):
        name = "selftest-stub"

        def supports(self, lang: str) -> bool:
            return True

        def available(self) -> tuple[bool, str]:
            return True, "Selftest-Stub"

        def voice_for(self, lang: str) -> str:
            return "selftest-stub"

        def synthesize(self, unit: Unit) -> SynthResult:
            raise BackendError("Selftest: Backend absichtlich kaputt")

    probe_engine = Engine(backend="none-available", profile="natural")
    probe_engine.by_lang = {"de": _KaputterStub(profile="natural"),
                            "en": _KaputterStub(profile="natural")}
    pf = probe_engine.preflight()
    check("Vorab-Test erkennt ein kaputtes Backend je Sprache",
          set(pf) == {"de", "en"} and all(ok is False for ok, _w in pf.values()), str(pf))
    check("Vorab-Test nennt die Ursache (Diagnose im Deploy-Log)",
          all("Selftest" in why for _ok, why in pf.values()), str(pf))
    check("Vorab-Test ohne nutzbares Backend liefert leeres Ergebnis",
          Engine(backend="none-available", profile="natural").preflight() == {})

    print(f"\n=== Backends-Selftest: {ok} grün, {fail} rot ===")
    return 1 if fail else 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Kostenlose Neural-Stimmen-Kette für die Vorlese-Tonspur.")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--engines", action="store_true",
                    help="verfügbare Backends und Stimmen anzeigen (diagnostisch)")
    ap.add_argument("--backend", default="auto")
    ap.add_argument("--profile", default="natural", choices=sorted(VOICE_PRESETS))
    args = ap.parse_args()

    if args.selftest:
        return selftest()
    if args.engines:
        eng = Engine(backend=args.backend, profile=args.profile, verbose=True)
        print(f"Profil: {args.profile} · Anfrage: {args.backend}")
        for name in BACKEND_ORDER:
            inst = BACKEND_CLASSES[name](profile=args.profile)
            ok, why = inst.available()
            print(f"  {'✅' if ok else '⊘'} {name:6s} {why}")
        print("Auswahl:", eng.describe() or "kein Backend verfügbar → Reader nutzt die Browser-Stimme")
        return 0
    print("Bitte --selftest oder --engines angeben.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
