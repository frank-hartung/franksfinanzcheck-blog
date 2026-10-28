#!/usr/bin/env python3
"""Mehrere Fokus-Keywords pro Artikel – Prüfung und Vorschlag (28.10.2026).

WARUM DIESE DATEI EXISTIERT
===========================
Yoast Premium erlaubt mehrere Fokus-Keywords pro Beitrag. Das ist keine
Spielerei: Der Blog bedient pro Artikel oft eine Hauptintention („DSL
Wechselbonus sichern") und zwei bis drei Nebenintentionen („Internet-
vertrag wechseln", „Cashback DSL"). Bisher standen diese Begriffe nur in
`keywords:` – einer ungeordneten Liste, aus der niemand erkennt, welcher
Begriff der wichtigste ist und ob er im Text überhaupt ankommt.

Diese Prüfung liest deshalb ein eigenes, geordnetes Feld:

    keywords_fokus: ["DSL-Wechselbonus sichern", "Internetvertrag wechseln"]

Der ERSTE Eintrag ist das Primär-Keyword (Hauptintention), die weiteren
sind Sekundär-Keywords. Fehlt das Feld, ist das KEIN Fehler, sondern eine
Empfehlung (F9, P3) – 97 bestehende Artikel werden nicht nachträglich rot.

REGELN (jede mit Selbsttest-Fall)
---------------------------------
  F1  Struktur: 1–5 Einträge, je 1–5 Wörter, ≤ 60 Zeichen, keine Dubletten
  F2  Primär-Keyword steht im Titel
  F3  Primär-Keyword steht im ersten Absatz (Suchintention sofort sichtbar)
  F4  Primär-Keyword steht in mindestens einer H2 (Gliederung folgt dem Thema)
  F5  Primär-Keyword steht in der Meta-Description
  F6  Jedes Sekundär-Keyword kommt im Fließtext vor
  F7  Keyword-Dichte des Primär-Keywords zwischen 0,4 % und 2,5 %
  F8  Kannibalisierung: derselbe Primär-Keyword auf mehreren Seiten
  F9  Feld fehlt (Empfehlung, kein Gate)

WAS HIER BEWUSST NICHT PASSIERT
-------------------------------
Kein „SEO-Score". Keine Punktzahl, die suggeriert, ein Text sei „80 %
gut". Jeder Befund nennt Datei, Regel, Messwert und den nächsten Schritt.
Ein grüner Lauf heißt: die formalen Bedingungen sind erfüllt – nicht, dass
der Text gut ist oder rankt.

Umlaute: Verglichen wird casefold + umlautgefaltet (ä→ae, ß→ss). Ein
Keyword „günstiges Girokonto" gilt also auch dann als vorhanden, wenn der
Text „guenstiges Girokonto" schreibt – die Schreibweise ist eine
Rechtschreibfrage, kein SEO-Befund.

Nutzung:
    python3 scripts/fokus_keywords.py                 # Prüfung
    python3 scripts/fokus_keywords.py --json          # maschinenlesbar
    python3 scripts/fokus_keywords.py --bericht x.md  # Markdown-Bericht
    python3 scripts/fokus_keywords.py --vorschlag     # Feld-Vorschläge
    python3 scripts/fokus_keywords.py --selftest

Exit: 0 ohne Gate-Befund, 1 bei Befund, 2 bei Eingabefehlern.
"""
from __future__ import annotations

import argparse
import contextlib
import glob
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import date

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")

FELD = "keywords_fokus"
MAX_FOKUS = 5
MAX_WOERTER = 5
MAX_ZEICHEN = 60
DICHTE_MIN = 0.4   # Prozent; darunter trägt das Keyword den Text nicht
DICHTE_MAX = 2.5   # Prozent; darüber liest es sich als Keyword-Stuffing

# Generische Anfänge, die als Fokus-Keyword nichts taugen ("die besten …").
STOPPWOERTER = {
    "ab", "als", "am", "an", "auch", "auf", "aus", "bei", "beim", "bis", "das",
    "dass", "dem", "den", "der", "des", "die", "dieser", "ein", "eine", "einem",
    "einen", "einer", "es", "für", "fuer", "im", "in", "ist", "mit", "nach",
    "oder", "so", "und", "vom", "von", "vor", "was", "wie", "wo", "zu", "zum",
    "zur", "über", "ueber",
}

CONTENT_GLOBS = (
    "content/posts/*/index.md",
    "content/posts/*.md",
    "content/pillar/*/index.md",
)
SKIP_BASENAMES = {"_index.md"}

try:  # PyYAML ist in requirements-ci.in gepinnt; ohne es bleibt die Wache stumm.
    import yaml
except ImportError:  # pragma: no cover - Umgebung ohne Abhängigkeiten
    yaml = None  # type: ignore[assignment]


# --------------------------------------------------------------------------
#  Text- und Frontmatter-Grundlagen
# --------------------------------------------------------------------------
def split_frontmatter(text: str) -> tuple[dict, str]:
    """Frontmatter + Body. Kaputtes YAML liefert ({}, Body) statt Ausnahme."""
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?(.*)$", text, re.S)
    if not m or yaml is None:
        return {}, (m.group(2) if m else text)
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return {}, m.group(2)
    return (data if isinstance(data, dict) else {}), m.group(2)


def normalisiere(text: str) -> str:
    """Vergleichsform: kleingeschrieben, umlautgefaltet, nur Wortzeichen.

    Bewusst nicht `unicodedata.normalize` allein: „ü" und „ue" sollen
    gleich behandelt werden, weil beides im Blog vorkommt.
    """
    text = (text or "").casefold()
    for alt, neu in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(alt, neu)
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _woerter(text: str) -> list[str]:
    return normalisiere(text).split()


def _enthaelt(text: str, phrase: str) -> bool:
    """Phrasentreffer auf Wortgrenzen, nicht als Teilwort.

    „konto“ darf nicht in „kontoführung“ treffen – sonst meldet die Prüfung
    ein Keyword als vorhanden, das im Text gar nicht als Begriff steht.
    """
    nadel = _woerter(phrase)
    if not nadel:
        return False
    heu = _woerter(text)
    n = len(nadel)
    return any(heu[i:i + n] == nadel for i in range(len(heu) - n + 1))


def _zaehle(text: str, phrase: str) -> int:
    nadel = _woerter(phrase)
    if not nadel:
        return 0
    heu = _woerter(text)
    n = len(nadel)
    return sum(1 for i in range(len(heu) - n + 1) if heu[i:i + n] == nadel)


def ohne_code(text: str) -> str:
    """Zeilenweise Code-Blöcke entfernen – ohne mehrzeilige Regexe.

    Ein `re.sub(r"```.*?```", …, flags=re.S)` ist auf mehrzeiliger Eingabe
    der Klassiker für polynomiale Rückverfolgung (CLAUDE.md, Regel 6:
    `py/polynomial-redos` ist ein Sicherheitsfund). Ein Zaun ist zeilenweise
    eindeutig: ``` öffnet, ``` schließt. Das ist schneller UND beweisbar.
    """
    zeilen: list[str] = []
    drin = False
    for zeile in text.splitlines():
        if zeile.lstrip().startswith("```"):
            drin = not drin
            zeilen.append("")
            continue
        zeilen.append("" if drin else zeile)
    return "\n".join(zeilen)


def fliess_text(body: str) -> str:
    """Body ohne Code, Shortcodes und HTML – das ist der messbare Fließtext.

    Shortcodes und HTML-Attribute sind Markup, kein Inhalt (dieselbe Grenze
    wie im internal_linker, dort aus einem echten Build-Schaden gelernt).
    Alle Muster sind zeilen- bzw. längenbeschränkt – keine mehrzeiligen
    Lazy-Quantoren.
    """
    text = ohne_code(body)
    text = re.sub(r"`[^`\n]*`", " ", text)
    text = re.sub(r"\{\{[<%][^>%]{0,500}[>%]\}\}", " ", text)
    text = re.sub(r"</?[A-Za-z][^>\n]*>", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return text


def absaetze(body: str) -> list[str]:
    """Absätze des Fließtexts, Überschriften und Tabellen ausgenommen."""
    blocks = re.split(r"\n\s*\n", fliess_text(body))
    return [b.strip() for b in blocks if b.strip() and not b.lstrip().startswith(("#", "|", ">"))]


def ueberschriften(body: str, stufe: int = 2) -> list[str]:
    muster = r"^#{%d} (.+)$" % stufe
    return re.findall(muster, fliess_text(body), re.M)


def parse_fokus(fm: dict) -> list[str]:
    """`keywords_fokus` als Liste von Strings (leer, wenn nicht gesetzt)."""
    wert = fm.get(FELD)
    if isinstance(wert, str):
        return [wert.strip()] if wert.strip() else []
    if isinstance(wert, list):
        return [str(v).strip() for v in wert if str(v).strip()]
    return []


@dataclass
class Befund:
    datei: str
    regel: str
    schwere: str
    text: str
    massnahme: str

    def als_dict(self) -> dict:
        return {"datei": self.datei, "regel": self.regel, "schwere": self.schwere,
                "text": self.text, "massnahme": self.massnahme}


@dataclass
class Seitenstand:
    """Was eine Seite über ihre Fokus-Keywords sagt – Grundlage für F8."""
    datei: str
    titel: str
    fokus: list[str] = field(default_factory=list)

    @property
    def primaer(self) -> str:
        return self.fokus[0] if self.fokus else ""


# --------------------------------------------------------------------------
#  Prüfung eines Dokuments
# --------------------------------------------------------------------------
def pruefe_dokument(datei: str, text: str) -> tuple[list[Befund], Seitenstand]:
    fm, body = split_frontmatter(text)
    titel = str(fm.get("title") or "")
    beschreibung = str(fm.get("description") or "")
    fokus = parse_fokus(fm)
    stand = Seitenstand(datei=datei, titel=titel, fokus=fokus)
    befunde: list[Befund] = []

    def add(regel: str, schwere: str, text_: str, massnahme: str) -> None:
        befunde.append(Befund(datei, regel, schwere, text_, massnahme))

    if not fokus:
        add("F9", "P3", f"Kein `{FELD}` gesetzt – Hauptintention nicht benannt.",
            f"Ein bis drei Begriffe eintragen, wichtigster zuerst: "
            f"`{FELD}: [\"…\"]`. Vorschlag: --vorschlag.")
        return befunde, stand

    # F1 – Struktur
    if len(fokus) > MAX_FOKUS:
        add("F1", "P2", f"{len(fokus)} Fokus-Keywords (max. {MAX_FOKUS}).",
            "Auf höchstens fünf Begriffe kürzen; jedes weitere verwässert die Hauptintention.")
    gesehen: set[str] = set()
    for i, kw in enumerate(fokus, 1):
        nw = len(_woerter(kw))
        norm = normalisiere(kw)
        label = "Primär-Keyword" if i == 1 else f"Sekundär-Keyword {i - 1}"
        if not norm:
            add("F1", "P2", f"{label} ist leer.", "Streichen oder durch einen Begriff ersetzen.")
            continue
        if nw > MAX_WOERTER:
            add("F1", "P2", f"{label} „{kw}“: {nw} Wörter (max. {MAX_WOERTER}).",
                "Kürzen – ein Fokus-Keyword ist ein Begriff, kein Satz.")
        if len(kw) > MAX_ZEICHEN:
            add("F1", "P2", f"{label} „{kw}“: {len(kw)} Zeichen (max. {MAX_ZEICHEN}).",
                "Kürzen; lange Phrasen kommen im Text praktisch nicht vor.")
        if _woerter(kw) and all(w in STOPPWOERTER for w in _woerter(kw)):
            add("F1", "P2", f"{label} „{kw}“ besteht nur aus Funktionswörtern.",
                "Inhaltswort ergänzen – Suchanfragen bestehen aus Begriffen.")
        if norm in gesehen:
            add("F1", "P2", f"{label} „{kw}“ ist doppelt.",
                "Doppelte Einträge entfernen; Dubletten zählen als Keyword-Stuffing.")
        gesehen.add(norm)

    primaer = fokus[0]
    fliess = fliess_text(body)
    absatz1 = absaetze(body)
    h2 = ueberschriften(body, 2)
    woerter_gesamt = len(_woerter(fliess))

    # F2 – Title
    if primaer.strip() and not _enthaelt(titel, primaer):
        add("F2", "P2", f"Primär-Keyword „{primaer}“ fehlt im Titel.",
            "Titel so schreiben, dass die Hauptintention in den ersten 60 Zeichen steht.")
    # F3 – erster Absatz
    if primaer.strip() and absatz1 and not _enthaelt(absatz1[0], primaer):
        add("F3", "P2", f"Primär-Keyword „{primaer}“ fehlt im ersten Absatz.",
            "Ersten Absatz auf die Suchintention ausrichten – er entscheidet über den Absprung.")
    # F4 – Gliederung
    if primaer.strip() and h2 and not any(_enthaelt(h, primaer) for h in h2):
        add("F4", "P3", f"Primär-Keyword „{primaer}“ steht in keiner H2.",
            "Eine Zwischenüberschrift nach dem Begriff benennen – das gliedert den Text.")
    # F5 – Description
    if primaer.strip() and not _enthaelt(beschreibung, primaer):
        add("F5", "P2", f"Primär-Keyword „{primaer}“ fehlt in der Description.",
            "Description mit dem Begriff beginnen; sie ist der Verkaufsgrund in der SERP.")
    # F6 – Sekundär-Keywords im Text
    for i, kw in enumerate(fokus[1:], 2):
        if normalisiere(kw) and not _enthaelt(fliess, kw):
            add("F6", "P2", f"Sekundär-Keyword „{kw}“ kommt im Fließtext nicht vor.",
                "Abschnitt dazu ergänzen oder den Begriff aus dem Feld nehmen – "
                "ein Keyword ohne Text ist eine Behauptung.")
    # F7 – Dichte des Primär-Keywords
    if normalisiere(primaer) and woerter_gesamt >= 100:
        treffer = _zaehle(fliess, primaer)
        dichte = treffer * len(_woerter(primaer)) / woerter_gesamt * 100
        if dichte > DICHTE_MAX:
            add("F7", "P2", f"Dichte „{primaer}“: {dichte:.1f} % bei {treffer} Treffern "
                         f"({DICHTE_MAX} % Obergrenze).",
                "Wiederholungen durch Varianten und Pronomen ersetzen – Dichte ist kein Rankingfaktor.")
        elif dichte < DICHTE_MIN:
            add("F7", "P3", f"Dichte „{primaer}“: {dichte:.1f} % bei {treffer} Treffern "
                         f"({DICHTE_MIN} % Untergrenze).",
                "Begriff an den Stellen nennen, an denen er fachlich hingehört; "
                "nicht künstlich einstreuen.")
    return befunde, stand


def kannibalisierung(staende: list[Seitenstand]) -> list[Befund]:
    """F8 – derselbe Primär-Keyword auf mehreren Seiten.

    Das ist der teuerste SEO-Fehler überhaupt: Zwei Seiten konkurrieren um
    dieselbe Suchanfrage, Google wählt eine aus, beide verlieren. Yoast
    Premium zeigt das als „Keyword cannibalization" – hier als Befund mit
    den beteiligten Dateien.
    """
    gruppen: dict[str, list[Seitenstand]] = {}
    for stand in staende:
        norm = normalisiere(stand.primaer)
        if norm:
            gruppen.setdefault(norm, []).append(stand)
    befunde: list[Befund] = []
    for norm, seiten in gruppen.items():
        if len(seiten) < 2:
            continue
        for stand in seiten:
            andere = ", ".join(s.datei for s in seiten if s.datei != stand.datei)
            befunde.append(Befund(
                stand.datei, "F8", "P2",
                f"Primär-Keyword „{stand.primaer}“ konkurriert mit: {andere}",
                "Eines der beiden Dokumente auf eine eigene Intention ausrichten oder "
                "konsolidieren (Weiterleitung) – sonst teilen sich beide die Signale."))
    return befunde


# --------------------------------------------------------------------------
#  Vorschläge aus den vorhandenen `keywords`
# --------------------------------------------------------------------------
def vorschlag_fokus(fm: dict, vergeben: set[str]) -> list[str]:
    """Belegt `keywords_fokus` aus `keywords:` – ohne Kannibalisierung.

    Bewusst nur ein Vorschlag, keine Änderung: Die Hauptintention eines
    Artikels ist eine redaktionelle Entscheidung. Die Funktion wählt
    Begriffe, die als Phrase brauchbar sind (2–4 Wörter, keine reinen
    Funktionswörter), nicht bereits Primär-Keyword einer anderen Seite sind
    und nicht doppelt vorkommen.
    """
    kandidaten: list[str] = []
    for roh in fm.get("keywords") or []:
        kw = str(roh).strip()
        norm = normalisiere(kw)
        if not norm or norm in vergeben or norm in {normalisiere(k) for k in kandidaten}:
            continue
        nw = len(_woerter(kw))
        if not 2 <= nw <= 4 or len(kw) > MAX_ZEICHEN:
            continue
        if all(w in STOPPWOERTER for w in _woerter(kw)):
            continue
        kandidaten.append(kw)
        if len(kandidaten) >= 3:
            break
    return kandidaten


# --------------------------------------------------------------------------
#  Repo-Lauf
# --------------------------------------------------------------------------
def sammle_dateien(root: str = BLOG_DIR) -> list[str]:
    dateien: list[str] = []
    for muster in CONTENT_GLOBS:
        dateien += glob.glob(os.path.join(root, muster))
    return sorted(p for p in set(dateien) if os.path.basename(p) not in SKIP_BASENAMES)


def ist_live(fm: dict, heute: str | None = None) -> bool:
    """Drafts und Zukunftsartikel sind keine SEO-Baustelle.

    `heute` und FF_HEUTE existieren für hermetische Tests: Ein Test, der
    vom Kalender abhängt, wird irgendwann ohne Codeänderung rot.
    """
    if fm.get("draft") is True:
        return False
    heute = heute or os.environ.get("FF_HEUTE") or date.today().isoformat()
    datum = str(fm.get("date") or "")
    if datum[:10] > heute:
        return False
    return True


def lauf(root: str = BLOG_DIR) -> tuple[list[Befund], list[Seitenstand], int]:
    befunde: list[Befund] = []
    staende: list[Seitenstand] = []
    dateien = sammle_dateien(root)
    for pfad in dateien:
        rel = os.path.relpath(pfad, root)
        with open(pfad, encoding="utf-8") as fh:
            text = fh.read()
        fm, _ = split_frontmatter(text)
        if not ist_live(fm):
            continue
        gefunden, stand = pruefe_dokument(rel, text)
        befunde += gefunden
        staende.append(stand)
    befunde += kannibalisierung(staende)
    return befunde, staende, len(dateien)


def bericht_md(befunde: list[Befund], staende: list[Seitenstand]) -> str:
    zeilen = ["# Fokus-Keywords – Bericht", "",
              f"Geprüfte Seiten: {len(staende)} · Befunde: {len(befunde)}", ""]
    if not befunde:
        zeilen.append("Keine Befunde. Die formalen Bedingungen sind erfüllt – "
                      "das ist keine Aussage über Inhalt oder Ranking.")
        return "\n".join(zeilen) + "\n"
    # F9 ist eine flächendeckende Empfehlung, kein Einzelfall: 76-mal
    # derselbe Absatz ist ein Bericht, den niemand liest. Er wird deshalb
    # EINMAL erklärt und dann als Liste der Dateien gezeigt.
    f9 = [b for b in befunde if b.regel == "F9"]
    befunde = [b for b in befunde if b.regel != "F9"]
    if f9:
        zeilen += [f"## Empfehlung: Hauptintention benennen (F9, {len(f9)} Seiten)", "",
                   "In diesen Dateien fehlt `keywords_fokus`. Das ist kein Fehler – "
                   "aber ohne benannte Hauptintention prüfen F2–F7 nichts.", "",
                   "Vorschläge für alle Seiten: `npm run fokus:vorschlag`.", ""]
        zeilen += [f"- `{b.datei}`" for b in sorted(f9, key=lambda b: b.datei)]
        zeilen.append("")
    nach_schwere: dict[str, list[Befund]] = {}
    for b in befunde:
        nach_schwere.setdefault(b.schwere, []).append(b)
    for schwere in ("P1", "P2", "P3"):
        gruppe = nach_schwere.get(schwere)
        if not gruppe:
            continue
        zeilen += [f"## {schwere} ({len(gruppe)})", ""]
        for b in gruppe:
            zeilen += [f"### {b.datei} · {b.regel}",
                       f"- **Befund:** {b.text}",
                       f"- **Maßnahme:** {b.massnahme}", ""]
    return "\n".join(zeilen) + "\n"


def vorschlaege(root: str = BLOG_DIR, limit: int = 20) -> list[dict]:
    """Seiten ohne `keywords_fokus` erhalten einen paste-fertigen Vorschlag."""
    ergebnis: list[dict] = []
    staende: list[Seitenstand] = []
    rohdaten: list[tuple[str, dict]] = []
    for pfad in sammle_dateien(root):
        rel = os.path.relpath(pfad, root)
        with open(pfad, encoding="utf-8") as fh:
            fm, _ = split_frontmatter(fh.read())
        if not ist_live(fm):
            continue
        rohdaten.append((rel, fm))
        staende.append(Seitenstand(rel, str(fm.get("title") or ""), parse_fokus(fm)))
    vergeben = {normalisiere(s.primaer) for s in staende if s.primaer}
    for rel, fm in rohdaten:
        if parse_fokus(fm):
            continue
        kandidaten = vorschlag_fokus(fm, vergeben)
        if not kandidaten:
            continue
        ergebnis.append({
            "datei": rel,
            "keywords_fokus": kandidaten,
            "yaml": f'{FELD}: [{", ".join(json.dumps(k, ensure_ascii=False) for k in kandidaten)}]',
        })
        vergeben.add(normalisiere(kandidaten[0]))
        if len(ergebnis) >= limit:
            break
    return ergebnis


def selftest() -> int:
    """Sabotage-Proben: Jede Regel muss auslösen, die Gegenprobe nicht."""
    if yaml is None:
        print("🛑 Selbsttest: PyYAML fehlt – Wache nicht scharf.")
        return 2
    text_100 = " ".join(["Wort"] * 100)
    gut = f"""---
title: "Strom sparen: Ratgeber für den Alltag"
description: "Strom sparen im Alltag: Stromfresser finden, Tarife vergleichen und Abschläge planen – mit Rechenbeispielen."
date: 2026-09-01
draft: false
keywords_fokus: ["Strom sparen", "Stromfresser finden"]
---

Strom sparen beginnt mit dem Blick auf den Zähler. {text_100}

## Strom sparen: wo die Kosten entstehen

Wer Stromfresser finden will, spart sofort. {text_100}
"""
    fails: list[str] = []

    def regeln(text: str) -> list[str]:
        return [b.regel for b in pruefe_dokument("content/posts/x/index.md", text)[0]]

    if (got := regeln(gut)) != []:
        fails.append(f"Gegenprobe erzeugt Befunde: {sorted(set(got))}")
    # F9: Feld fehlt → Empfehlung P3, nicht P2
    ohne = gut.replace('keywords_fokus: ["Strom sparen", "Stromfresser finden"]\n', "")
    b_ohne, _ = pruefe_dokument("content/posts/x/index.md", ohne)
    if [b.regel for b in b_ohne] != ["F9"] or b_ohne[0].schwere != "P3":
        fails.append(f"F9 falsch: {[(b.regel, b.schwere) for b in b_ohne]}")
    # F2: Primär nicht im Titel
    if "F2" not in regeln(gut.replace('title: "Strom sparen: Ratgeber für den Alltag"',
                                      'title: "Energie im Alltag"').replace(
            "## Strom sparen: wo die Kosten entstehen", "## Energie: wo die Kosten entstehen")):
        fails.append("F2 (Titel) löst nicht aus")
    # F3: Primär nicht im ersten Absatz
    if "F3" not in regeln(gut.replace("Strom sparen beginnt mit dem Blick auf den Zähler.",
                                      "Der Zähler lohnt einen Blick.")):
        fails.append("F3 (erster Absatz) löst nicht aus")
    # F4: Primär in keiner H2
    if "F4" not in regeln(gut.replace("## Strom sparen: wo die Kosten entstehen",
                                      "## Wo die Kosten entstehen")):
        fails.append("F4 (H2) löst nicht aus")
    # F5: Primär nicht in der Description
    if "F5" not in regeln(gut.replace('description: "Strom sparen im Alltag',
                                      'description: "Energie im Alltag')):
        fails.append("F5 (Description) löst nicht aus")
    # F6: Sekundär-Keyword fehlt im Text
    if "F6" not in regeln(gut.replace("Wer Stromfresser finden will", "Wer Verbraucher prüft")):
        fails.append("F6 (Sekundär-Keyword im Text) löst nicht aus")
    # F7: Stuffing
    voll = " ".join(["Strom sparen"] * 30)
    if "F7" not in regeln(gut.replace(text_100, voll)):
        fails.append("F7 (zu hohe Dichte) löst nicht aus")
    # F1: zu viele Einträge und Dublette
    viele = gut.replace('keywords_fokus: ["Strom sparen", "Stromfresser finden"]',
                        'keywords_fokus: ["strom sparen", "strom sparen", "a", "b", "c", "d"]')
    if "F1" not in regeln(viele):
        fails.append("F1 (Struktur) löst nicht aus")
    # F8: Kannibalisierung über zwei Dokumente
    a, sa = pruefe_dokument("a.md", gut)
    b, sb = pruefe_dokument("b.md", gute_zweitseite())
    kan = kannibalisierung([sa, sb])
    if len(kan) != 2 or {k.datei for k in kan} != {"a.md", "b.md"}:
        fails.append(f"F8 (Kannibalisierung) falsch: {[k.als_dict() for k in kan]}")
    if kan and not all(k.regel == "F8" for k in kan):
        fails.append("F8 liefert falsche Regel-IDs")
    # Umlaut-Faltung: „guenstig" trifft „günstig"
    if not _enthaelt("Ein guenstiges Girokonto ohne Gebuehren", "günstiges Girokonto"):
        fails.append("Umlaut-Faltung greift nicht")
    # Kein Teilwort-Treffer
    if _enthaelt("Die Kontoführung ist kostenlos", "Konto"):
        fails.append("Teilwort-Treffer (Kontoführung ~ Konto) wird als Treffer gewertet")
    # Vorschlag: keine Übernahme eines bereits vergebenen Primär-Keywords
    fm = {"keywords": ["Strom sparen für Haushalte", "Tagesgeld Vergleich 2026", "Konto"]}
    v = vorschlag_fokus(fm, {normalisiere("Strom sparen für Haushalte")})
    if any(normalisiere(k) == normalisiere("Strom sparen für Haushalte") for k in v):
        fails.append("Vorschlag übernimmt ein bereits vergebenes Primär-Keyword")
    if not v:
        fails.append("Vorschlag findet keinen geeigneten Begriff")
    # Bericht bleibt ohne Befund ehrlich (keine Ranking-Aussage)
    md = bericht_md([], [sa])
    if "keine Aussage über Inhalt oder Ranking" not in md:
        fails.append("Bericht ohne Befund enthält keine Ehrlichkeitsgrenze")
    if fails:
        for f in fails:
            print(f"❌ Fokus-Keywords: {f}")
        return 2
    print("✅ Fokus-Keywords: Selbsttest bestanden – Struktur, Titel, erster Absatz, "
          "H2, Description, Sekundär-Keywords, Dichte, Kannibalisierung und "
          "Umlaut-Faltung sind belegt.")
    return 0


def gute_zweitseite() -> str:
    return """---
title: "Strom sparen im Haushalt: die größten Irrtümer"
description: "Strom sparen im Haushalt: Irrtümer, Zahlen und die Reihenfolge, in der sich Sparen wirklich lohnt."
date: 2026-09-02
draft: false
keywords_fokus: ["Strom sparen"]
---

Strom sparen im Haushalt ist kein Hexenwerk, sondern eine Reihenfolge.

## Strom sparen: die Reihenfolge

Zuerst die Verbraucher, dann der Tarif.
"""


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Befunde als JSON")
    parser.add_argument("--bericht", metavar="PFAD", help="Markdown-Bericht schreiben")
    parser.add_argument("--vorschlag", action="store_true",
                        help="Vorschläge für fehlende keywords_fokus ausgeben")
    parser.add_argument("--limit", type=int, default=20, help="max. Vorschläge")
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--root", default=BLOG_DIR, help="Repository-Wurzel")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    # Bei maschinenlesbarer Ausgabe gehört der Selbsttest nach stderr –
    # sonst ist stdout kein gültiges JSON mehr (und jeder Pipe-Aufruf bricht).
    if args.json or args.vorschlag:
        with contextlib.redirect_stdout(sys.stderr):
            if selftest() != 0:
                return 2
    elif selftest() != 0:
        return 2
    if args.vorschlag:
        print(json.dumps(vorschlaege(args.root, args.limit), ensure_ascii=False, indent=2))
        return 0

    befunde, staende, geprueft = lauf(args.root)
    if args.bericht:
        ziel = os.path.abspath(args.bericht)
        os.makedirs(os.path.dirname(ziel) or ".", exist_ok=True)
        with open(ziel, "w", encoding="utf-8") as fh:
            fh.write(bericht_md(befunde, staende))
        print(f"Bericht: {ziel}")
    if args.json:
        print(json.dumps({"geprueft": geprueft, "seiten": len(staende),
                          "befunde": [b.als_dict() for b in befunde]},
                         ensure_ascii=False, indent=2))
    else:
        f9 = [b for b in befunde if b.regel == "F9"]
        for b in sorted((b for b in befunde if b.regel != "F9"),
                        key=lambda b: (b.schwere, b.datei, b.regel)):
            print(f"  [{b.regel}/{b.schwere}] {b.datei}: {b.text}")
        if f9:
            print(f"  [F9/P3] {len(f9)} Seiten ohne `{FELD}` – Empfehlung, kein Gate "
                  f"(Bericht: --bericht).")
        gate = sum(1 for b in befunde if b.schwere in ("P1", "P2"))
        print(f"Fokus-Keywords: {len(staende)} Seiten, {len(befunde)} Befunde "
              f"({gate} mit Gate-Wirkung).")
    return 1 if any(b.schwere in ("P1", "P2") for b in befunde) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
