#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skills_portfolio.py – welches Fremd-Skill dient welchem Blog-Thema?

WARUM DIESE WACHE EXISTIERT (01.11.2026)
----------------------------------------
Die Bibliothek unter `.claude/skills/` ist an einem Tag von 18 auf 56
Fremd-Skills gewachsen und wieder auf 50 geschrumpft. Der Grund für das
Schrumpfen war kein Gefühl, sondern eine Frage: **Welche Themen bedient der
Blog überhaupt?** Sie war richtig – und sie hatte keinen Ort. Ohne diesen Ort
zahlt jede Session die Beschreibung jedes Skills mit, auch der elf, die kein
Thema haben, und niemand kann begründen, welcher gehen darf.

`data/skill_portfolio.yaml` ist der Ort, dieser Lauf ist sein Vollstrecker:

  P1  Vollständigkeit: jedes installierte Fremd-Skill steht entweder unter
      `produktion` (dient einem Thema) oder unter `ausgeschlossen` (mit
      Grund, Entscheidung, Frist). Ein Skill ohne Entscheidung ist Dauerlast
      ohne Zweck – und still.
  P2  Themen tragen einen Beleg: jedes Thema hat eine `quelle`, und die
      Datei existiert. Ein Thema ohne Beleg wird nicht bedient, sondern
      behauptet; ein Kanal ohne Beleg existiert nicht.
  P3  Budget: die Summe der Beschreibungen aller Themen-Skills liegt unter
      `budget_kb`. Das ist die Grenze des *Themenbetriebs* – K9 in
      `skills_vertrag.py` begrenzt die Gesamtsumme.
  P4  Deckung: jedes Thema hat mindestens ein Skill, und jedes `kanaele`
      eines Skills steht in der Kanalliste. Ein Skill, der an einem Kanal
      hängt, den es nicht gibt, arbeitet für niemanden.
  P5  Fristen: eine `faellig` in der Vergangenheit ist eine **Warnung**, nie
      ein Befund – dieselbe Linie wie K6. Wer eine Frist setzt, will
      entscheiden; das Gate soll ihn nicht bestrafen, sondern erinnern.
  P6  Kein Skill doppelt: ein Name steht nicht gleichzeitig unter
      `produktion` und `ausgeschlossen`.
  P7  Themenart: ein Kanal-Thema (`art: kanal`) braucht mindestens ein Skill;
      ein Inhaltsthema (`art: inhalt`, die sechs Themenwelten) wird von der
      Content-Engine bedient und muss **Artikel** tragen. Das ist die
      Unterscheidung, die „Thema ohne Marketing-Skill" von „Thema ohne
      Substanz" trennt.

Der Lauf ist absichtlich *abhängigkeitsfrei*: die YAML-Datei wird mit einem
kleinen eigenen Leser geparst (kein PyYAML), damit das Gate in jedem
CI-Image läuft und der Selbsttest offline bleibt.

Aufruf:
  python3 scripts/skills_portfolio.py             # prüfen (Befund = Exit 1)
  python3 scripts/skills_portfolio.py --md        # Markdown für die Lauf-Summary
  python3 scripts/skills_portfolio.py --json      # maschinenlesbar
  python3 scripts/skills_portfolio.py --selftest  # Sabotage-Schutz, offline

Exit: 0 = sauber · 1 = Befund · 2 = Hausfehler (unlesbare Quelle, Selbsttest)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from collections import namedtuple
from datetime import date
from pathlib import Path

BLOG_DIR = Path(__file__).resolve().parent.parent
PORTFOLIO = Path("data/skill_portfolio.yaml")
SKILL_ORDNER = Path(".claude/skills")
EIGEN_PRÄFIX = "ff-"
KB_MAX = 56.0

Fund = namedtuple("Fund", "klasse pfad stelle meldung")
Warn = namedtuple("Warn", "klasse pfad stelle meldung")


def kurz(self) -> str:
    ort = f"{self.pfad}" + (f":{self.stelle}" if self.stelle else "")
    return f"[{self.klasse}] {ort} – {self.meldung}"


Fund.kurz = kurz  # type: ignore[attr-defined]
Warn.kurz = kurz  # type: ignore[attr-defined]


# ---------------------------------------------------------------- YAML (Teilmenge)
def _skalar(wert: str):
    wert = wert.strip()
    if not wert:
        return ""
    if wert.startswith("["):
        innen = wert.strip("[]").strip()
        return [_skalar(x) for x in _teile(innen)] if innen else []
    if wert.startswith("{"):
        # Inline-Abbildung: {grund: "g", faellig: "2099-12-31"} – dieselbe Form,
        # in der dieses Repo kurze Ausnahmen notiert.
        innen = wert.strip("{}").strip()
        out = {}
        for teil in _teile(innen):
            k, _, v = teil.partition(":")
            out[k.strip().strip("\"'")] = _skalar(v)
        return out
    if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in "\"'":
        return wert[1:-1]
    if wert in ("true", "false"):
        return wert == "true"
    if wert in ("null", "~"):
        return None
    try:
        return int(wert)
    except ValueError:
        pass
    try:
        return float(wert)
    except ValueError:
        return wert


def _teile(text: str) -> list[str]:
    """Teilt an Kommas, die nicht in Anführungszeichen oder Klammern stehen."""
    out, puffer, tiefe, quote = [], "", 0, ""
    for zeichen in text:
        if quote:
            puffer += zeichen
            if zeichen == quote:
                quote = ""
            continue
        if zeichen in "\"'":
            quote = zeichen
            puffer += zeichen
        elif zeichen in "[{":
            tiefe += 1
            puffer += zeichen
        elif zeichen in "]}":
            tiefe -= 1
            puffer += zeichen
        elif zeichen == "," and tiefe == 0:
            out.append(puffer.strip())
            puffer = ""
        else:
            puffer += zeichen
    if puffer.strip():
        out.append(puffer.strip())
    return out


def _zeilen_yaml(text: str) -> list[tuple[int, str]]:
    out = []
    for roh in text.split("\n"):
        if not roh.strip() or roh.lstrip().startswith("#"):
            continue
        tiefe = len(roh) - len(roh.lstrip(" "))
        out.append((tiefe, roh.strip()))
    return out


def parse_yaml(text: str) -> dict:
    """Liest die Formen, die dieses Repo in `data/*.yaml` schreibt.

    Bewusst kein vollständiger YAML-Parser: Abbildungen, Listen, Listen von
    Abbildungen, Skalare, `[a, b]`-Inline-Listen und `{k: v}`-Inline-Maps.
    Alles darüber hinaus endet als Zeichenkette – dann meckert die Wache,
    statt zu raten.
    """
    zeilen = _zeilen_yaml(text)
    wert, _ = _block(zeilen, 0, zeilen[0][0] if zeilen else 0)
    return wert if isinstance(wert, dict) else {}


def _naechster_block(zeilen, i: int, tiefe: int):
    """Ein Wert, der in der nächsten Zeile steht.

    YAML erlaubt eine Liste auf **derselben** Einrückung wie ihr Schlüssel
    („strom:", darunter „- skill: …"). Genau diese Form schreibt das Repo –
    wer sie nicht liest, hält jedes Thema für leer.
    """
    if i >= len(zeilen):
        return None, i
    kind_tiefe = zeilen[i][0]
    if kind_tiefe < tiefe:
        return None, i
    return _block(zeilen, i, kind_tiefe)


def _block(zeilen, i: int, tiefe: int):
    if i >= len(zeilen):
        return None, i
    if zeilen[i][1].startswith("- "):
        return _liste(zeilen, i, tiefe)
    return _abbildung(zeilen, i, tiefe)


def _liste(zeilen, i: int, tiefe: int):
    out = []
    while i < len(zeilen) and zeilen[i][0] == tiefe and zeilen[i][1].startswith("- "):
        rest = zeilen[i][1][2:].strip()
        i += 1
        if not rest:
            wert, i = _block(zeilen, i, tiefe + 2)
            out.append(wert)
        elif ":" in rest and not rest.startswith(("[", "{", '"', "'")):
            k, _, v = rest.partition(":")
            eintrag: dict = {}
            i = _paar(zeilen, i, tiefe + 2, k.strip(), v, eintrag)
            unter, i = _abbildung_fortsetzung(zeilen, i, tiefe + 2)
            eintrag.update(unter)
            out.append(eintrag)
        else:
            out.append(_skalar(rest))
    return out, i


def _paar(zeilen, i: int, kinder_tiefe: int, schluessel: str, wert_text: str, ziel: dict) -> int:
    if wert_text.strip():
        ziel[schluessel] = _skalar(wert_text)
        return i
    wert, i = _naechster_block(zeilen, i, kinder_tiefe)
    ziel[schluessel] = wert
    return i


def _abbildung_fortsetzung(zeilen, i: int, tiefe: int):
    out: dict = {}
    while i < len(zeilen) and zeilen[i][0] == tiefe and not zeilen[i][1].startswith("- "):
        k, _, v = zeilen[i][1].partition(":")
        i += 1
        i = _paar(zeilen, i, tiefe, k.strip(), v, out)
    return out, i


def _abbildung(zeilen, i: int, tiefe: int):
    out: dict = {}
    while i < len(zeilen) and zeilen[i][0] == tiefe and not zeilen[i][1].startswith("- "):
        k, _, v = zeilen[i][1].partition(":")
        i += 1
        i = _paar(zeilen, i, tiefe, k.strip(), v, out)
    return out, i


# ---------------------------------------------------------------- Lesen
def _text(root: Path, rel: str | Path) -> str | None:
    p = root / rel
    try:
        return p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def _description(root: Path, name: str) -> str:
    text = _text(root, f"{SKILL_ORDNER}/{name}/SKILL.md") or ""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    fm = m.group(1) if m else ""
    d = re.search(r"^description:\s*(.*?)(?=\n[a-z_-]+:|\Z)", fm, re.S | re.M)
    return " ".join((d.group(1) if d else "").strip().strip('"').split())


def _tokens(root: Path, name: str) -> int:
    """Vier Zeichen ≈ ein Token – die Hausformel, dieselbe wie in K9."""
    return len(_description(root, name)) // 4


def _installiert(root: Path) -> set[str]:
    ordner = root / SKILL_ORDNER
    if not ordner.is_dir():
        return set()
    return {p.name for p in ordner.iterdir() if p.is_dir() and not p.name.startswith(EIGEN_PRÄFIX)}


def _datum(wert) -> date | None:
    try:
        return date.fromisoformat(str(wert).strip())
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- Prüfungen
def lade(root: Path) -> tuple[dict, list[Fund]]:
    text = _text(root, PORTFOLIO)
    if text is None:
        return {}, [Fund("P0", str(PORTFOLIO), "", "fehlt – ohne Portfolio ist kein Skill einem "
                                                       "Thema zugeordnet und jede Dauerlast unbegründet.")]
    daten = parse_yaml(text)
    if not isinstance(daten, dict) or not daten:
        return {}, [Fund("P0", str(PORTFOLIO), "", "unlesbar oder leer – die Zuordnung fehlt.")]
    return daten, []


def _produktion(daten: dict) -> dict[str, list[dict]]:
    prod = daten.get("produktion") or {}
    return {k: (v or []) for k, v in prod.items()} if isinstance(prod, dict) else {}


def p1_vollstaendigkeit(root: Path, daten: dict) -> list[Fund]:
    funde: list[Fund] = []
    installiert = _installiert(root)
    zugeordnet = set()
    for eintraege in _produktion(daten).values():
        for e in eintraege or []:
            if isinstance(e, dict) and e.get("skill"):
                zugeordnet.add(str(e["skill"]))
    ausgeschlossen = daten.get("ausgeschlossen") or {}
    if isinstance(ausgeschlossen, dict):
        zugeordnet |= set(ausgeschlossen)
    for name in sorted(installiert - zugeordnet):
        funde.append(Fund("P1", f"{SKILL_ORDNER}/{name}", "",
                          "weder einem Thema zugeordnet noch mit Grund ausgeschlossen – "
                          "das Skill zahlt in jeder Session Dauerlast, ohne dass jemand "
                          "entschieden hat wofür. In `data/skill_portfolio.yaml` eintragen "
                          "oder entfernen."))
    return funde


def p2_belege(root: Path, daten: dict) -> list[Fund]:
    funde: list[Fund] = []
    themen = daten.get("themen") or {}
    if not isinstance(themen, dict) or not themen:
        return [Fund("P2", str(PORTFOLIO), "themen", "keine Themen definiert – dann ist P4 nicht prüfbar.")]
    for tid, t in themen.items():
        if not isinstance(t, dict):
            funde.append(Fund("P2", str(PORTFOLIO), str(tid), "Thema ohne Angaben (name/quelle)."))
            continue
        quelle = str(t.get("quelle") or "").strip()
        if not quelle:
            funde.append(Fund("P2", str(PORTFOLIO), str(tid), "Thema ohne `quelle` – ein Thema ohne "
                                                              "Beleg wird behauptet, nicht bedient."))
        elif not (root / quelle).exists():
            funde.append(Fund("P2", f"{PORTFOLIO}:{tid}", quelle,
                              "Belegpfad existiert nicht – das Thema ist im Baum nicht auffindbar."))
    kanaele = daten.get("kanaele") or {}
    for name, pfad in (kanaele.items() if isinstance(kanaele, dict) else []):
        if not (root / str(pfad)).exists():
            funde.append(Fund("P2", f"{PORTFOLIO}:kanaele", str(name),
                              f"Kanal-Beleg `{pfad}` fehlt – ein Kanal, der nicht existiert, "
                              "darf keinem Skill Arbeit zuweisen."))
    return funde


def p3_budget(root: Path, daten: dict) -> list[Fund]:
    prod = _produktion(daten)
    if not prod:
        return []
    summe = 0
    for eintraege in prod.values():
        for e in eintraege or []:
            if isinstance(e, dict) and e.get("skill"):
                summe += _tokens(root, str(e["skill"]))
    grenze = float(daten.get("budget_kb") or KB_MAX)
    kb = summe / 1000.0
    if kb <= grenze:
        return []
    return [Fund("P3", str(PORTFOLIO), f"{kb:.1f} KB",
                 f"Themen-Skills zahlen {summe} Tokens ({kb:.1f} KB) Dauerlast und liegen über "
                 f"dem Budget von {grenze:.0f} KB. Drei Wege, alle ehrlich: Beschreibung kürzen, "
                 "Skill aus dem Thema nehmen (dann P1) oder die Grenze mit Begründung anheben.")]


def p4_deckung(root: Path, daten: dict) -> list[Fund]:
    funde: list[Fund] = []
    themen = daten.get("themen") or {}
    prod = _produktion(daten)
    kanaele = daten.get("kanaele") or {}
    kanaele = set(kanaele) if isinstance(kanaele, dict) else set()
    if not themen:
        return funde
    for tid, t in themen.items():
        art = str((t or {}).get("art") or "").strip()
        if art not in ("inhalt", "kanal"):
            funde.append(Fund("P4", f"{PORTFOLIO}:themen", str(tid),
                              "Thema ohne `art` (inhalt|kanal) – ohne diese Angabe ist nicht "
                              "entscheidbar, ob ein Skill fehlt oder nur nicht nötig ist."))
            continue
        if art == "kanal" and not prod.get(tid):
            funde.append(Fund("P4", f"{PORTFOLIO}:themen", str(tid),
                              "Kanal-Thema ohne Skill – es steht in der Liste, aber niemand bedient es."))
    for tid, eintraege in prod.items():
        if themen and tid not in themen:
            funde.append(Fund("P4", f"{PORTFOLIO}:produktion", str(tid),
                              "Thema in `produktion`, aber nicht unter `themen` definiert – "
                              "dann fehlt ihm der Beleg (P2)."))
        for e in eintraege or []:
            if not isinstance(e, dict) or not e.get("skill"):
                continue
            if not str(e.get("rolle") or "").strip():
                funde.append(Fund("P4", f"{PORTFOLIO}:{tid}", str(e["skill"]),
                                  "ohne `rolle` – ein Skill ohne benannte Aufgabe ist eine Vermutung."))
            for kanal in e.get("kanaele") or []:
                if kanaele and kanal not in kanaele:
                    funde.append(Fund("P4", f"{PORTFOLIO}:{tid}", str(e["skill"]),
                                      f"Kanal `{kanal}` ist nicht in `kanaele` belegt – der Skill "
                                      "arbeitet für einen Kanal, den dieser Blog nicht hat."))
    return funde


def p5_fristen(daten: dict, stichtag: date) -> list[Warn]:
    warnungen: list[Warn] = []
    aus = daten.get("ausgeschlossen") or {}
    for name, eintrag in (aus.items() if isinstance(aus, dict) else []):
        if not isinstance(eintrag, dict):
            continue
        for feld in ("grund", "entscheidung", "faellig"):
            if not str(eintrag.get(feld) or "").strip():
                warnungen.append(Warn("P5", f"{PORTFOLIO}:ausgeschlossen", f"{name}.{feld}",
                                      "fehlt – ein Ausschluss ohne Frist ist eine stille Abschaffung."))
        frist = _datum(eintrag.get("faellig"))
        if frist and frist < stichtag:
            warnungen.append(Warn("P5", f"{PORTFOLIO}:ausgeschlossen", name,
                                  f"Ausschluss abgelaufen ({frist.isoformat()}) – neu entscheiden: "
                                  "aufnehmen oder Frist mit Grund verlängern."))
    return warnungen


def _artikel_je_thema(root: Path) -> dict[str, int]:
    """Zählt Artikel über `pillar:` im Frontmatter – so, wie die Website zählt.

    Der Pillar-Ordner enthält nur `_index.md`; die Artikel liegen unter
    `content/posts/…` und tragen `pillar: strom-sparen`. Eine Prüfung, die
    Dateien im Pillar-Ordner zählt, misst die Kachel, nicht den Bestand.
    """
    zaehler: dict[str, int] = {}
    basis = root / "content"
    if not basis.is_dir():
        return zaehler
    muster = re.compile(r"^pillar:\s*[\"']?([a-zA-Z0-9_-]+)", re.M)
    for datei in basis.rglob("*.md"):
        if datei.name == "_index.md":
            continue
        try:
            kopf = datei.read_text(encoding="utf-8", errors="replace")[:4000]
        except OSError:
            continue
        treffer = muster.search(kopf)
        if treffer:
            zaehler[treffer.group(1)] = zaehler.get(treffer.group(1), 0) + 1
    return zaehler


def p7_inhaltsthema(root: Path, daten: dict) -> list[Fund]:
    """Ein Inhaltsthema muss Artikel tragen – sonst ist es eine leere Kachel.

    Die sechs Themenwelten werden nicht von Marketing-Skills bedient, sondern
    von der Content-Engine: Themenpool, Reserve, Faktenfrische, eine Latte.
    Ein Inhaltsthema ohne Artikel ist deshalb kein „fehlendes Skill", sondern
    eine Behauptung auf der Startseite – und genau das prüft diese Klasse.
    """
    funde: list[Fund] = []
    zaehler = _artikel_je_thema(root)
    for tid, t in (daten.get("themen") or {}).items():
        if not isinstance(t, dict) or str(t.get("art") or "") != "inhalt":
            continue
        if not str(t.get("quelle") or "").strip():
            continue  # P2 meldet das schon
        artikel = zaehler.get(str(tid), 0)
        if artikel < 1:
            funde.append(Fund("P7", str(PORTFOLIO), str(tid),
                              "Inhaltsthema ohne einen einzigen Artikel (`pillar:` im Frontmatter) – "
                              "eine Themenwelt ohne Artikel ist eine leere Kachel, kein Thema."))
    return funde


def p6_doppelt(daten: dict) -> list[Fund]:
    funde: list[Fund] = []
    prod = {str(e.get("skill")) for eintraege in _produktion(daten).values()
            for e in eintraege or [] if isinstance(e, dict) and e.get("skill")}
    aus = daten.get("ausgeschlossen") or {}
    doppelt = sorted(prod & set(aus if isinstance(aus, dict) else {}))
    for name in doppelt:
        funde.append(Fund("P6", str(PORTFOLIO), name,
                          "steht gleichzeitig unter `produktion` und `ausgeschlossen` – "
                          "eine Entscheidung, zwei Antworten."))
    return funde


# ---------------------------------------------------------------- Bilanz
def befunde(root: Path, stichtag: date | None = None) -> tuple[list[Fund], list[Warn], dict]:
    tag = stichtag or date.today()
    daten, fehler = lade(root)
    if fehler:
        return fehler, [], {}
    funde = (p1_vollstaendigkeit(root, daten) + p2_belege(root, daten)
             + p3_budget(root, daten) + p4_deckung(root, daten) + p6_doppelt(daten)
             + p7_inhaltsthema(root, daten))
    warnungen = p5_fristen(daten, tag)
    prod = _produktion(daten)
    skills = [str(e["skill"]) for eintraege in prod.values() for e in eintraege or []
              if isinstance(e, dict) and e.get("skill")]
    kennzahlen = {
        "themen": len(daten.get("themen") or {}),
        "skills_mit_thema": len(set(skills)),
        "tokens_mit_thema": sum(_tokens(root, s) for s in set(skills)),
        "ausgeschlossen": len(daten.get("ausgeschlossen") or {}),
        "installiert": len(_installiert(root)),
    }
    kennzahlen["tokens_gesamt"] = sum(_tokens(root, s) for s in _installiert(root))
    return funde, warnungen, kennzahlen


def bericht(funde: list[Fund], warnungen: list[Warn], k: dict, geprueft: bool = True) -> str:
    z = ["## Skill-Portfolio – welches Skill dient welchem Thema", ""]
    if k:
        z += [f"Themen **{k['themen']}** · Skills mit Thema **{k['skills_mit_thema']}** "
              f"(≈ {k['tokens_mit_thema']} Tokens) · ausgeschlossen **{k['ausgeschlossen']}** · "
              f"installiert **{k['installiert']}** (≈ {k['tokens_gesamt']} Tokens gesamt).", ""]
    if not funde and not warnungen:
        z.append("✅ Befundfrei: jedes Fremd-Skill dient einem belegten Thema oder ist mit Grund, "
                 "Entscheidung und Frist ausgeschlossen; das Themen-Budget hält.")
    if warnungen:
        z += ["", "**Warnungen (kein Blocker):**", ""] + [f"- {w.kurz()}" for w in warnungen]
    if funde:
        z += ["", f"**🛑 {len(funde)} Befund(e):**", ""] + [f"- `{f.kurz()}`" for f in funde]
        z += ["", "Heilung: Skill einem Thema zuordnen (mit `rolle` und belegtem Kanal), mit "
                  "Grund/Entscheidung/Frist ausschließen oder entfernen. Ein Skill, das niemand "
                  "zuordnet, bezahlt trotzdem jede Session."]
    return "\n".join(z)


# ---------------------------------------------------------------- Selbsttest
def _schreibe(wurzel: Path, rel: str, text: str) -> None:
    (wurzel / rel).parent.mkdir(parents=True, exist_ok=True)
    (wurzel / rel).write_text(text, encoding="utf-8")


def _fixture(wurzel: Path, *, yaml: str | None = None, skills: dict | None = None,
             belege: dict | None = None, budget: float | None = None) -> Path:
    """Ein Baum mit zwei Fremd-Skills, einem Thema, einem Kanal und Belegen."""
    _schreibe(wurzel, "CLAUDE.md", "# Kern\n\n`ff-eins` ist der Router.\n")
    beschreibung = ("Benutzen, wenn an der Suche gearbeitet wird: Titel, Snippet, Zitierbarkeit "
                    "in KI-Antworten. Auslöser sind auch 'warum rankt das nicht' und 'AEO'.")
    # Der Wert im Dict IST die Beschreibung – so lässt sich P3 (Budget) an einer
    # gewachsenen Bibliothek beweisen, ohne 20 echte Skills anzulegen.
    for name, beschr in (skills or {"fremd-a": beschreibung, "fremd-b": beschreibung}).items():
        _schreibe(wurzel, f"{SKILL_ORDNER}/{name}/SKILL.md",
                  f"---\nname: {name}\ndescription: \"{beschr}\"\n---\n\n# X\n")
    for rel, inhalt in (belege or {"content/pillar/strom": "x", "scripts/gsc.py": "x",
                                   "layouts": "x"}).items():
        _schreibe(wurzel, rel, inhalt)
    text = yaml if yaml is not None else f"""schema: 1
themen:
  strom:
    art: kanal
    name: "Strom"
    quelle: "content/pillar/strom"
kanaele:
  suchmaschine: "scripts/gsc.py"
  website: "layouts"
produktion:
  strom:
  - skill: fremd-a
    rolle: "Snippet"
    kanaele: [suchmaschine]
ausgeschlossen:
  fremd-b:
    grund: "kein Kanal"
    entscheidung: "nicht installiert"
    faellig: "2099-12-31"
budget_kb: {budget if budget is not None else 56.0}
"""
    _schreibe(wurzel, str(PORTFOLIO), text)
    return wurzel


def selftest() -> int:
    geprueft = 0
    fehler: list[str] = []

    def erzwinge(name: str, wurzel: Path, klasse: str | None, *, nur_warnung: bool = False):
        nonlocal geprueft
        funde, warnungen, _ = befunde(wurzel, stichtag=date(2027, 1, 15))
        geprueft += 1
        if klasse is None:
            if funde:
                fehler.append(f"{name}: Gegenprobe erwartet 0 Befunde, gekommen: "
                              + "; ".join(f.kurz() for f in funde[:3]))
        elif nur_warnung:
            if [f for f in funde if f.klasse == klasse]:
                fehler.append(f"{name}: {klasse} darf höchstens warnen, hat aber Befunde.")
            if not [w for w in warnungen if w.klasse == klasse]:
                fehler.append(f"{name}: {klasse} hat nicht gewarnt.")
        elif klasse not in {f.klasse for f in funde}:
            fehler.append(f"{name}: erwartete {klasse}, gekommen: "
                          + (", ".join(sorted({f.klasse for f in funde})) or "nichts"))

    with tempfile.TemporaryDirectory() as tmp:
        # 1) Gegenprobe
        erzwinge("Gegenprobe sauber", _fixture(Path(tmp) / "sauber"), None)

        # 2) P1: installiert, aber nirgends entschieden
        erzwinge("P1 Skill ohne Entscheidung",
                 _fixture(Path(tmp) / "p1", skills={"fremd-a": "B" * 300, "fremd-c": "B" * 300}),
                 "P1")

        # 3) P2: Belegpfad fehlt
        erzwinge("P2 fehlender Beleg",
                 _fixture(Path(tmp) / "p2", belege={"scripts/gsc.py": "x", "layouts": "x"}),
                 "P2")

        # 4) P2: Kanal ohne Beleg
        yaml_kanal = """schema: 1
themen:
  strom:
    art: kanal
    name: "Strom"
    quelle: "content/pillar/strom"
kanaele:
  website: "layouts"
produktion:
  strom:
  - skill: fremd-a
    rolle: "Snippet"
    kanaele: [newsletter]
ausgeschlossen:
  fremd-b: {grund: "g", entscheidung: "e", faellig: "2099-12-31"}
"""
        erzwinge("P2 Kanal ohne Beleg", _fixture(Path(tmp) / "p2b", yaml=yaml_kanal), "P4")

        # 5) P7: Inhaltsthema ohne Artikel (eine leere Kachel).
        yaml_leer_kachel = """schema: 1
themen:
  strom:
    art: inhalt
    name: "Strom"
    quelle: "content/pillar/leer"
kanaele:
  website: "layouts"
produktion: {}
ausgeschlossen: {}
"""
        w = _fixture(Path(tmp) / "p7", yaml=yaml_leer_kachel)
        _schreibe(w, "content/pillar/leer/_index.md", "# Kachel ohne Artikel\n")
        erzwinge("P7 leere Themenwelt", w, "P7")
        # Gegenprobe: ein Artikel mit `pillar:` füllt die Kachel – dieselbe Prüfung schweigt.
        _schreibe(w, "content/posts/2026-01-01-x.md", "---\npillar: strom\n---\n\n# X\n")
        funde, _, _ = befunde(w, stichtag=date(2027, 1, 15))
        geprueft += 1
        if [f for f in funde if f.klasse == "P7"]:
            fehler.append("P7: ein Artikel mit `pillar:` muss die Kachel füllen.")

        # 5b) P4: Thema ohne `art` ist nicht entscheidbar.
        yaml_ohne_art = """schema: 1
themen:
  strom:
    art: kanal
    name: "Strom"
    quelle: "content/pillar/strom"
kanaele:
  website: "layouts"
produktion: {}
ausgeschlossen: {}
"""
        erzwinge("P4 Thema ohne Art", _fixture(Path(tmp) / "p4c", yaml=yaml_ohne_art), "P4")

        # 6) P3: Themen-Budget gerissen
        viele = {f"fremd-{i}": "B" * 3000 for i in range(20)}
        yaml_budget = "schema: 1\nthemen:\n  strom:\n    name: S\n    quelle: content/pillar/strom\n"
        yaml_budget += "kanaele:\n  website: layouts\nproduktion:\n  strom:\n"
        yaml_budget += "".join(f"  - skill: fremd-{i}\n    rolle: r\n    kanaele: [website]\n"
                               for i in range(20))
        yaml_budget += "ausgeschlossen: {}\nbudget_kb: 10\n"
        erzwinge("P3 Budget gerissen",
                 _fixture(Path(tmp) / "p3", yaml=yaml_budget, skills=viele, budget=10), "P3")

        # 6) P4: Thema ohne Skill
        yaml_leer = """schema: 1
themen:
  strom:
    art: kanal
    name: "Strom"
    quelle: "content/pillar/strom"
  gas:
    art: kanal
    name: "Gas"
    quelle: "content/pillar/strom"
kanaele:
  website: "layouts"
produktion:
  strom:
  - skill: fremd-a
    rolle: "Snippet"
    kanaele: [website]
ausgeschlossen:
  fremd-b: {grund: "g", entscheidung: "e", faellig: "2099-12-31"}
"""
        erzwinge("P4 Thema ohne Skill", _fixture(Path(tmp) / "p4", yaml=yaml_leer), "P4")

        # 7) P4: Skill ohne rolle
        yaml_ohne_rolle = """schema: 1
themen:
  strom:
    art: kanal
    name: "Strom"
    quelle: "content/pillar/strom"
kanaele:
  website: "layouts"
produktion:
  strom:
  - skill: fremd-a
    kanaele: [website]
ausgeschlossen:
  fremd-b: {grund: "g", entscheidung: "e", faellig: "2099-12-31"}
"""
        erzwinge("P4 Skill ohne Rolle", _fixture(Path(tmp) / "p4b", yaml=yaml_ohne_rolle), "P4")

        # 8) P5: abgelaufene Frist warnt nur
        yaml_frist = """schema: 1
themen:
  strom:
    art: kanal
    name: "Strom"
    quelle: "content/pillar/strom"
kanaele:
  website: "layouts"
produktion:
  strom:
  - skill: fremd-a
    rolle: "Snippet"
    kanaele: [website]
ausgeschlossen:
  fremd-b: {grund: "g", entscheidung: "e", faellig: "2026-12-31"}
"""
        erzwinge("P5 abgelaufene Frist",
                 _fixture(Path(tmp) / "p5", yaml=yaml_frist), "P5", nur_warnung=True)

        # 9) P5: Ausschluss ohne Grund ist eine stille Abschaffung – Warnung
        yaml_ohne_grund = """schema: 1
themen:
  strom:
    art: kanal
    name: "Strom"
    quelle: "content/pillar/strom"
kanaele:
  website: "layouts"
produktion:
  strom:
  - skill: fremd-a
    rolle: "Snippet"
    kanaele: [website]
ausgeschlossen:
  fremd-b: {entscheidung: "e", faellig: "2099-12-31"}
"""
        erzwinge("P5 Ausschluss ohne Grund",
                 _fixture(Path(tmp) / "p5b", yaml=yaml_ohne_grund), "P5", nur_warnung=True)

        # 10) P6: gleichzeitig produktion und ausgeschlossen
        yaml_doppelt = """schema: 1
themen:
  strom:
    art: kanal
    name: "Strom"
    quelle: "content/pillar/strom"
kanaele:
  website: "layouts"
produktion:
  strom:
  - skill: fremd-a
    rolle: "Snippet"
    kanaele: [website]
ausgeschlossen:
  fremd-a: {grund: "g", entscheidung: "e", faellig: "2099-12-31"}
"""
        erzwinge("P6 doppelte Entscheidung",
                 _fixture(Path(tmp) / "p6", yaml=yaml_doppelt), "P6")

        # 11) P0: Datei fehlt komplett
        wurzel = _fixture(Path(tmp) / "p0")
        (wurzel / PORTFOLIO).unlink()
        erzwinge("P0 Datei fehlt", wurzel, "P0")

        # 12) Uhr-Freiheit: dasselbe Urteil an einem anderen Stichtag
        funde_a, _, _ = befunde(_fixture(Path(tmp) / "uhr"), stichtag=date(2027, 1, 15))
        funde_b, _, _ = befunde(_fixture(Path(tmp) / "uhr"), stichtag=date(2027, 1, 15))
        geprueft += 1
        if [f.kurz() for f in funde_a] != [f.kurz() for f in funde_b]:
            fehler.append("Selbsttest hängt an der Wanduhr: derselbe Stand meldet unterschiedlich.")

    if fehler:
        print("🛑 skills_portfolio --selftest FEHLERHALFT (der Selbsttest prüft die Detektoren):")
        for f in fehler:
            print("   -", f)
        return 2
    print(f"✅ skills_portfolio --selftest OK ({geprueft} eingefrorene Fälle: Gegenprobe, "
          "Skill ohne Entscheidung, fehlender Themen-Beleg, Kanal ohne Beleg, Budget, Thema ohne "
          "Skill, Skill ohne Rolle, abgelaufene Frist, Ausschluss ohne Grund, doppelte "
          "Entscheidung, fehlende Datei, leere Themenwelt, Thema ohne Art, Uhr-Freiheit).")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Skill-Portfolio: Thema, Kanal, Budget, Ausschluss")
    ap.add_argument("--selftest", action="store_true", help="Sabotage-Schutz (offline, uhrfest)")
    ap.add_argument("--json", action="store_true", help="Maschinenausgabe")
    ap.add_argument("--md", action="store_true", help="Markdown für die Lauf-Summary")
    ap.add_argument("root", nargs="?", default=None, help="Prüfwurzel (Standard: Repo)")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    root = Path(args.root).resolve() if args.root else BLOG_DIR
    if not (root / "CLAUDE.md").is_file():
        print(f"🛑 skills_portfolio: {root} ist keine Prüfwurzel (CLAUDE.md fehlt).", file=sys.stderr)
        return 2
    funde, warnungen, kennzahlen = befunde(root)
    if args.json:
        print(json.dumps({
            "funde": [f._asdict() for f in funde],
            "warnungen": [w._asdict() for w in warnungen],
            "kennzahlen": kennzahlen,
        }, ensure_ascii=False, indent=1))
    else:
        print(bericht(funde, warnungen, kennzahlen))
        print(f"\nskills_portfolio: {kennzahlen.get('skills_mit_thema', 0)} Skill(s) mit Thema, "
              f"{kennzahlen.get('ausgeschlossen', 0)} ausgeschlossen, "
              f"{len(funde)} Befund(e), {len(warnungen)} Warnung(en).")
    return 1 if funde else 0


if __name__ == "__main__":
    sys.exit(main())
