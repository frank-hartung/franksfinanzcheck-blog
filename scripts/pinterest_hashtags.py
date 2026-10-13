#!/usr/bin/env python3
"""PINTEREST-HASHTAG-HYGIENE – die EINE Wahrheit für Pin-Hashtags (P8)

Befund #729 (13.10.2026): Ein Artikel trug fünf Hashtags in seiner
`pin_description`. Gefunden haben das zwei Stellen – geheilt hat es keine:

  * `pinterest_check.py` meldete „5 Hashtags (max. 3)" (Code P8) – der
    Watchdog öffnete dafür ein Issue und schloss es nie wieder: Der Befund
    wurde nicht geheilt (andere Klassen hatten Heiler, Hashtags keinen),
    und der Workflow schließt nur bei Exit 0. Es war der einzige offene
    Posten des Laufs – und er konnte jeden Tag nur erneut auftauchen.
  * `pinterest_seo_healer.py` (H6) sah dieselbe Klasse in seinem Report,
    hielt den Text aber weiter für „gültig" (Länge + kein `&`) und
    überschrieb ihn deshalb nie.

Dazu kam eine stille Lücke: Beide Prüfungen zählten Hashtags mit einem
Muster, das Umlaute ausschließt (`#([a-z0-9]+)` bzw. `[A-Za-z0-9]+`).
Damit war die Umlaut-Regel in beiden Dateien **toter Code** – und
`#zählerstand` oder `#ersteWohnung` im Bestand unsichtbar, obwohl beide
im Pin-Text stehen (Pinterest kann sie nicht als Themen-Tag lesen).

Die Regel (Pinterest-Profi-Standard, P8) steht ab jetzt an genau EINER
Stelle – hier. Jeder Pinterest-Schreiber importiert sie:

  H1  höchstens `HASHTAG_MAX` (3) Hashtags pro Beschreibung
  H2  nur `[a-z0-9]`: ASCII, klein – keine Umlaute, keine Großbuchstaben,
      kein Bindestrich, kein Emoji, keine Satzzeichen
  H3  `HASHTAG_MIN_LEN`–`HASHTAG_MAX_LEN` (3–24) Zeichen je Tag
  H4  ein Tag trägt Text: ein reines Zahlenschild (`#1`, `#2026`) ist
      kein Hashtag und wird weder gezählt noch erzeugt
  H5  kein Tag doppelt (gezählt wird nach Faltung, also case-insensitiv)
  H6  die Hashtags stehen als EIN Block am Ende der Beschreibung

Heilung (`heile`): entfernt alle Tag-Token, normalisiert die
behaltenen (Umlaut-Faltung → Kleinschreibung → `[a-z0-9]`) und hängt
die ersten `HASHTAG_MAX` als Block wieder an. Sie **erfindet nie ein
Thema**: gekappt wird hinten (die Reihenfolge im Text ist die
Priorität), und ein Tag, das sich nicht reparieren lässt, fällt weg.
Für bereits konforme Texte ist `heile` byte-identisch (Idempotenz).

Nutzung:
  python3 scripts/pinterest_hashtags.py --selftest        # Logik-Beweis (Exit 0/2)
  python3 scripts/pinterest_hashtags.py --wirkungsprobe   # Klasse am Fixture beweisen
  python3 scripts/pinterest_hashtags.py --pruefe "<Text>" # Befundliste (Exit 0/1)
  python3 scripts/pinterest_hashtags.py --heile "<Text>"  # Text + Änderungen (JSON)

Als Modul:
  from pinterest_hashtags import befunde, heile, tags_bauen
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata

# ---------------------------------------------------------------- Regel (H1–H6)
HASHTAG_MAX = 3
HASHTAG_MIN_LEN = 3
HASHTAG_MAX_LEN = 24
# Obergrenze der Pin-Beschreibung (Pinterest) – dieselbe Zahl wie P4/H6.
BESCHREIBUNG_MAX = 500

# Ein Tag-Token beginnt mit '#' und endet am nächsten Leerzeichen/weiteren '#'.
TAG_TOKEN = re.compile(r"#[^\s#]+")
# Nach der Faltung muss genau das übrig bleiben (H2 + H3 + H4).
GUELTIG = re.compile(rf"^(?=.*[a-z])[a-z0-9]{{{HASHTAG_MIN_LEN},{HASHTAG_MAX_LEN}}}$")
# Umlaut-Faltung (identisch zu den bisherigen Generatoren) + NFKD-Rest.
_FALTUNG = (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"))
_BUCHSTABE = re.compile(r"[a-z]")


def falte(text: str) -> str:
    """Umlaute → ae/oe/ue/ss, Akzente → Grundbuchstabe (NFKD)."""
    t = str(text or "").replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
    for a, b in _FALTUNG:
        t = t.replace(a, b)
    t = unicodedata.normalize("NFKD", t)
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.lower()


def normalisiere(token: str) -> str:
    """Ein Tag-Token (mit oder ohne '#') → kanonische Form `[a-z0-9]{3,24}`.

    'zählerstand' → 'zaehlerstand' · 'ersteWohnung' → 'erstewohnung'
    'DSL-Vergleich' → 'dslvergleich' · '5€-Tipp' → '5tipp' · '#' → ''
    """
    roh = str(token or "").lstrip("#")
    return "".join(re.findall(r"[a-z0-9]+", falte(roh)))


def ist_gueltig(tag: str) -> bool:
    """H2 + H3 + H4: nur [a-z0-9], 3–24 Zeichen, mindestens ein Buchstabe."""
    return bool(GUELTIG.match(str(tag or "")))


def ist_zahlenschild(token: str) -> bool:
    """H4: reines Zahlenschild (`#1`, `#2026`) – kein Themen-Tag."""
    roh = str(token or "").lstrip("#")
    return bool(roh) and not _BUCHSTABE.search(falte(roh)) and bool(re.search(r"[0-9]", roh))


def tags_in(text: str) -> list[str]:
    """Alle Tag-Token des Textes, roh und in Reihenfolge ('#umzug' …)."""
    return TAG_TOKEN.findall(str(text or ""))


def tags_normalisiert(text: str, mit_zahlenschild: bool = False) -> list[str]:
    """Faltete, entdoppelte Tags in Reihenfolge (ohne '#').

    Zahlenschilder zählen per Default nicht als Hashtag (H4).
    """
    out: list[str] = []
    for tok in tags_in(text):
        if not mit_zahlenschild and ist_zahlenschild(tok):
            continue
        tag = normalisiere(tok)
        if tag and tag not in out:
            out.append(tag)
    return out


def als_text(tags) -> str:
    """Tag-Liste → Block aus '#tag'-Wörtern."""
    return " ".join("#" + t for t in tags if t)


def _block_am_ende(text: str) -> bool:
    """H6: Hashtags stehen als ein geschlossener Block am Textende.

    Zahlenschilder (`#1`, `#2026`) sind keine Hashtags und zählen hier
    nicht mit – sonst würde der Satz „Rabatt #1 im Test" als Tag-Block
    gewertet."""
    tokens = [m for m in TAG_TOKEN.finditer(text)
              if not ist_zahlenschild(m.group(0))]
    if not tokens:
        return True
    if text[tokens[-1].end():].strip():
        return False
    for a, b in zip(tokens, tokens[1:]):
        if text[a.end():b.start()].strip():
            return False
    return True


def befunde(text: str, max_tags: int = HASHTAG_MAX) -> list[str]:
    """Meldungen zu einem Pin-Text – leer heißt konform (H1–H6)."""
    text = str(text or "")
    out: list[str] = []
    tokens = [t for t in tags_in(text) if not ist_zahlenschild(t)]
    if len(tokens) > max_tags:
        out.append(f"{len(tokens)} Hashtags (max. {max_tags})")
    gesehen: list[str] = []
    for tok in tokens:
        roh = tok.lstrip("#")
        tag = normalisiere(tok)
        if not tag:
            out.append(f"Hashtag {tok} ohne verwertbaren Inhalt (nur [a-z0-9])")
            continue
        if re.search(r"[äöüÄÖÜß]", str(tok)):
            out.append(f"Umlaut-Hashtag #{roh}")
        elif re.search(r"[A-ZÄÖÜ]", str(tok)):
            out.append(f"Hashtag #{roh} mit Großbuchstaben (nur [a-z0-9])")
        elif not GUELTIG.match(tag):
            out.append(f"Hashtag #{roh} ungültig (nur [a-z0-9], "
                       f"{HASHTAG_MIN_LEN}–{HASHTAG_MAX_LEN} Zeichen)")
        if tag in gesehen:
            out.append(f"Hashtag #{roh} doppelt (nach Faltung)")
        else:
            gesehen.append(tag)
    if not _block_am_ende(text):
        out.append("Hashtags stehen nicht als Block am Ende")
    return out


def ist_konform(text: str, max_tags: int = HASHTAG_MAX) -> bool:
    return not befunde(text, max_tags=max_tags)


def _kuerze(text: str, limit: int) -> str:
    """Wortgrenzen-Kürzung auf `limit` Zeichen (nur wenn nötig)."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    sp = cut.rfind(" ")
    if sp > 0:
        cut = cut[:sp]
    return cut.rstrip(" ,.;:–-") + "…"


def heile(text: str, max_tags: int = HASHTAG_MAX) -> tuple[str, list[str]]:
    """Heilt die Hashtag-Hygiene eines Pin-Textes.

    Rückgabe: (geheilter Text, Liste der Änderungen). Ein konformer Text
    kommt byte-identisch zurück (Idempotenz) – die Funktion ändert nie
    Prosa, sie ordnet nur die Tag-Token neu und faltet sie.
    """
    text = str(text or "")
    aenderungen: list[str] = []
    tokens = [t for t in tags_in(text) if not ist_zahlenschild(t)]
    if not tokens and not befunde(text, max_tags=max_tags):
        return text, aenderungen

    basis = TAG_TOKEN.sub("", text)
    basis = re.sub(r"[ \t]{2,}", " ", basis)
    basis = re.sub(r"\s+([.,;:!?])", r"\1", basis)
    basis = re.sub(r"\(\s*\)", "", basis).strip()

    behalten: list[str] = []
    verworfen: list[str] = []
    for tok in tokens:
        tag = normalisiere(tok)
        if tag not in behalten and tag not in verworfen:
            (behalten if ist_gueltig(tag) else verworfen).append(tag)
    gekappt = behalten[max_tags:]
    behalten = behalten[:max_tags]

    block = als_text(behalten)
    if block:
        basis = _kuerze(basis, max(HASHTAG_MIN_LEN, BESCHREIBUNG_MAX - len(block) - 1))
    else:
        basis = _kuerze(basis, BESCHREIBUNG_MAX)
    neu = (basis.rstrip() + " " + block).strip() if block else basis.rstrip() or text.strip()

    if len(tokens) > max_tags:
        aenderungen.append(f"Hashtags auf {max_tags} gekappt "
                           f"(entfernt: {als_text(gekappt) or '–'})")
    gefaltet = [t for t in tokens if normalisiere(t) != t.lstrip("#")]
    if gefaltet:
        aenderungen.append("Tags kanonisiert: "
                           + ", ".join(f"{t}→#{normalisiere(t)}" for t in gefaltet))
    if verworfen:
        erkennen = ", ".join(f"#{t}" if t else "„#“" for t in verworfen)
        aenderungen.append(f"unbrauchbare Tags entfernt: {erkennen}")
    if not _block_am_ende(text) and tokens:
        aenderungen.append("Tags als Block ans Textende gestellt")
    if neu != text and not aenderungen:
        aenderungen.append("Hashtag-Block normalisiert")
    return neu, aenderungen


def tags_bauen(keywords, slug: str = "", max_tags: int = HASHTAG_MAX) -> list[str]:
    """Themen-Tags aus Keywords + Slug – dieselbe Quelle wie bisher, eine Regel.

    Keywords zuerst (sie sind der Suchintent), der Slug zuletzt. Eine
    Phrase wird zusammengezogen ('DSL-Vergleich' → 'dslvergleich'), wie es
    die Pinterest-Generatoren seit dem 25.08.2026 tun.
    """
    pool = [k for k in (keywords or []) if k]
    if slug:
        pool.append(str(slug).replace("-", " "))
    out: list[str] = []
    for phrase in pool:
        for wort in str(phrase).split():
            tag = normalisiere(wort)
            if ist_gueltig(tag) and tag not in out:
                out.append(tag)
            if len(out) >= max_tags:
                return out[:max_tags]
    return out


# ---------------------------------------------------------------- Selbsttest
def _selftest() -> list[str]:
    """Sabotage-Schutz: prüft die Regel selbst, nicht das Modell."""
    fehler: list[str] = []
    if HASHTAG_MAX != 3:
        fehler.append("HASHTAG_MAX ≠ 3 (Pinterest-Profi-Standard)")
    if (HASHTAG_MIN_LEN, HASHTAG_MAX_LEN) != (3, 24):
        fehler.append("Tag-Längen verändert (H3)")
    if BESCHREIBUNG_MAX != 500:
        fehler.append("BESCHREIBUNG_MAX ≠ 500")
    # H2: Umlaut + Großbuchstabe MÜSSEN erkannt werden (toter Code war #729).
    if not any("Umlaut" in f for f in befunde("Text #zählerstand")):
        fehler.append("Umlaut-Hashtag wird nicht erkannt (H2)")
    if not any("Großbuchstaben" in f for f in befunde("Text #ersteWohnung")):
        fehler.append("Großbuchstaben-Hashtag wird nicht erkannt (H2)")
    if not any("max. 3" in f for f in befunde("#a1b #b2c #c3d #d4e")):
        fehler.append("H1 (max. 3) wird nicht erkannt")
    if not any("doppelt" in f for f in befunde("#umzug #Umzug")):
        fehler.append("Doppelter Tag wird nicht erkannt (H5)")
    if not any("Block am Ende" in f for f in befunde("#umzug Text danach")):
        fehler.append("Tag-Block nicht am Ende wird nicht erkannt (H6)")
    # H4: Zahlenschilder sind keine Hashtags.
    if befunde("Rabatt #1 im Test #2"):
        fehler.append("Zahlenschilder werden als Hashtag gewertet (H4)")
    # Positivprobe: saubere Texte bleiben still.
    sauber = ("*Werbung | Umzug geplant: So nimmst du Internet und Rufnummer mit. "
              "Mehr Spartipps auf FranksFinanzcheck! #umzug #internet #rufnummer")
    if befunde(sauber):
        fehler.append(f"konformer Text wird beanstandet: {befunde(sauber)}")
    if heile(sauber)[0] != sauber:
        fehler.append("Heilung verändert einen konformen Text (Idempotenz)")
    # Faltung + Kappung + Idempotenz am echten #729-Fall.
    fall = ("*Werbung | Beim Umzug entscheidet die Reihenfolge. Mehr Spartipps auf "
            "FranksFinanzcheck! #umzug #internet #rufnummer #dsl #wechsel")
    geheilt, aend = heile(fall)
    if "#umzug #internet #rufnummer" not in geheilt or "#dsl" in geheilt or "#wechsel" in geheilt:
        fehler.append(f"#729-Fall nicht gekappt: {geheilt!r}")
    if not aend:
        fehler.append("#729-Fall ohne Änderungsbeleg")
    if heile(geheilt)[0] != geheilt:
        fehler.append("Heilung ist nicht idempotent (zweiter Lauf ändert)")
    if len(geheilt) > BESCHREIBUNG_MAX:
        fehler.append("Heilung überschreitet die Beschreibungs-Obergrenze")
    if not ist_konform(geheilt):
        fehler.append(f"geheilter Text ist nicht konform: {befunde(geheilt)}")
    # Normalisierung: Umlaut-Fall und camelCase aus dem Bestand.
    if normalisiere("#zählerstand") != "zaehlerstand":
        fehler.append("Umlaut-Faltung defekt")
    if normalisiere("#ersteWohnung") != "erstewohnung":
        fehler.append("Kleinschreibung defekt")
    if tags_bauen(["Umzug Internet", "DSL-Vergleich"], "umzug-mit-internet") != \
            ["umzug", "internet", "dslvergleich"]:
        fehler.append(f"tags_bauen weicht ab: {tags_bauen(['Umzug Internet', 'DSL-Vergleich'], 'umzug-mit-internet')}")
    if len(tags_bauen(["a", "b", "c", "d", "e"], "f-g-h")) > HASHTAG_MAX:
        fehler.append("tags_bauen liefert mehr als HASHTAG_MAX")
    return fehler


def _wirkungsprobe() -> int:
    """Beweist die Klasse am Fixture: erkennen → heilen → Fixpunkt."""
    faelle = [
        ("#729 (fünf Tags)",
         "*Werbung | Beim Umzug entscheidet die Reihenfolge über zwei Wochen ohne "
         "Internet. Mehr Spartipps auf FranksFinanzcheck! #umzug #internet #rufnummer #dsl #wechsel",
         "*Werbung | Beim Umzug entscheidet die Reihenfolge über zwei Wochen ohne "
         "Internet. Mehr Spartipps auf FranksFinanzcheck! #umzug #internet #rufnummer"),
        ("Umlaut aus dem Bestand",
         "*Werbung | Gaszähler ablesen. #zählerstand #gas",
         "*Werbung | Gaszähler ablesen. #zaehlerstand #gas"),
        ("camelCase aus dem Bestand",
         "*Werbung | Der erste eigene Haushalt. #ersteWohnung #fixkosten",
         "*Werbung | Der erste eigene Haushalt. #erstewohnung #fixkosten"),
        ("Tag mitten im Satz",
         "*Werbung | #umzug Wir zeigen dir die Reihenfolge. #internet",
         "*Werbung | Wir zeigen dir die Reihenfolge. #umzug #internet"),
    ]
    fehler = 0
    for name, rein, erwartet in faelle:
        vorher = befunde(rein)
        neu, aend = heile(rein)
        nachher = befunde(neu)
        fix = heile(neu)[0]
        ok = bool(vorher) and not nachher and neu == erwartet and fix == neu
        print(f"  {'✅' if ok else '❌'} {name}: "
              f"{len(vorher)} Befund(e) → {len(aend)} Änderung(en) → Fixpunkt")
        if not ok:
            fehler += 1
            print(f"     erwartet: {erwartet!r}")
            print(f"     erhalten: {neu!r} (Befunde danach: {nachher})")
    print(("✅ WIRKUNGSPROBE bestanden – erkennen, heilen, Fixpunkt (4 Fälle)."
           if not fehler else f"❌ WIRKUNGSPROBE fehlgeschlagen ({fehler} Fall/Fälle)."))
    return 1 if fehler else 0


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        fehler = _selftest()
        if fehler:
            print("🛑 PINTEREST-HASHTAG-SELBSTTEST FEHLGESCHLAGEN:")
            for f in fehler:
                print(f"   {f}")
            return 2
        print("✅ Pinterest-Hashtag-Selbsttest ok (H1–H6, Idempotenz, #729-Fall).")
        return 0
    if "--wirkungsprobe" in argv:
        return _wirkungsprobe()
    if "--pruefe" in argv:
        text = argv[argv.index("--pruefe") + 1] if len(argv) > argv.index("--pruefe") + 1 else ""
        funde = befunde(text)
        print(json.dumps({"befunde": funde, "konform": not funde}, ensure_ascii=False))
        return 0 if not funde else 1
    if "--heile" in argv:
        text = argv[argv.index("--heile") + 1] if len(argv) > argv.index("--heile") + 1 else ""
        neu, aend = heile(text)
        print(json.dumps({"text": neu, "aenderungen": aend}, ensure_ascii=False))
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
