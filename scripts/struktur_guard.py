#!/usr/bin/env python3
# ============================================================
#  STRUKTUR-GUARD – Wache gegen Artikel-Zerfaserung
#  (Premium 30.09.2026, Issue #476 „Bestand-Gate: bestehende
#   Artikel brauchen Aufmerksamkeit“)
#
#  ANLASS (echter Schaden, nicht theoretisch):
#    `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler`
#    lief mit 22.599 Zeichen in das harte „zu-lang“-Kriterium des
#    Bestand-Gates (Deckel 22.000, SSOT length_policy.py). Ursache war
#    NICHT ein zu langer Artikel, sondern 15 nacheinander angehängte
#    Mini-Abschnitte aus den Politur-Runden 25–41
#    (PREMIUM-BLOG-AUDIT-2026-09-25.md): „Welche Reihenfolge …“,
#    „Welche zwei Geldlecks …“, „Welche kurze Freitagsfrage …“ –
#    jeder für sich 40–70 Wörter, inhaltlich überlappend, in Serie
#    an das Artikelende gehängt.
#
#  WARUM ES BISHER NIEMAND SAH – die strukturelle Lücke:
#    • length_guard.py heilt NUR nach oben (Artikel zu kurz → KI ergänzt).
#      Für die Gegenrichtung gab es keine Wache.
#    • check_length.py misst Zeichen und meldet erst beim harten Deckel –
#      also Wochen nachdem die Zerfaserung begonnen hat, und ohne die
#      Ursache zu benennen („braucht echte Textarbeit“).
#    • content_audit.py C1 prüft nur „zu dünn“ (Gesamt-Wortzahl), nicht
#      die Feinstruktur.
#    Ergebnis: Jede Politur-Runde durfte einen weiteren Mini-Abschnitt
#    anhängen, bis der Deckel fiel. Genau das verhindert diese Wache.
#
#  REGELN (deterministisch, ohne KI):
#    S1  MIKRO-ABSCHNITT: ein H2-Abschnitt mit weniger als
#        MIKRO_WORDS (90) Wörtern Fließtext. Kurze Struktur-Rubriken
#        (Kurzfassung, FAQ-Kopf, Quellen …) sind per Kanon befreit.
#    S2  SERIEN-SIGNATUR: drei oder mehr AUFEINANDERFOLGENDE H2, die
#        mit demselben Wort beginnen („Welche … / Welche … / Welche …“).
#        Das ist der Fingerabdruck angehängter Politur-Runden.
#    S3  ZERFASERUNG MIT ÜBERLÄNGE: Fließtext über dem Optimum
#        (length_policy opt_max_chars) UND mindestens ein Mikro-
#        Abschnitt. Das ist exakt die Lage, die #476 ausgelöst hat –
#        sie wird gemeldet, BEVOR der harte Deckel von 22.000 Zeichen
#        erreicht ist (Vorlauf statt Nachlauf).
#
#  SPERRKLINKE (der eigentliche Dauer-Schutz):
#    data/struktur_baseline.json hält je Artikel den akzeptierten Stand
#    (Mikro-Abschnitte, Serien). Die Wache lässt diesen Stand NUR
#    KLEINER WERDEN:
#      • Zuwachs (oder Neu-Artikel über NEU_TOLERANZ) → Fund, Exit 1.
#      • Rückgang → Baseline zieht automatisch nach (Klinke rastet ein).
#    Damit ist der Bestand ab heute eingefroren: Eine weitere Politur-
#    Runde, die einen Mini-Abschnitt anhängt, fällt sofort auf – statt
#    erst Wochen später als „zu lang“ im Bestand-Gate.
#
#  KEIN AUTO-FIX – bewusst. Abschnitte zusammenführen ist redaktionelle
#  Arbeit (Textverdichtung), kein deterministischer Eingriff. Die Wache
#  meldet, sie schreibt nie in Artikel.
#
#  SABOTAGE-SCHUTZ: eingefrorene Selbsttest-Fälle laufen VOR jeder
#  Bewertung; rot = Exit 2, und es wird nichts geschrieben (fail-closed,
#  Hausregel wie bei allen Wachen).
#
#  Aufruf:
#    python3 scripts/struktur_guard.py              # prüfen + Bericht
#    python3 scripts/struktur_guard.py --dry-run    # nichts schreiben
#    python3 scripts/struktur_guard.py --new-only   # nur heutige Geburten
#    python3 scripts/struktur_guard.py --json
#    python3 scripts/struktur_guard.py --selftest
#    python3 scripts/struktur_guard.py --seed-baseline   # Stand einfrieren
#
#  Exit: 0 = grün · 1 = Struktur-Fund (Regression) · 2 = Wache defekt
#  Ausgabe: STRUKTUR-REPORT.md · data/struktur_baseline.json ·
#           data/struktur_history.jsonl (append-only)
# ============================================================
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
POSTS_DIR = ROOT / "content" / "posts"
REPORT = ROOT / "STRUKTUR-REPORT.md"
BASELINE = ROOT / "data" / "struktur_baseline.json"
HISTORY = ROOT / "data" / "struktur_history.jsonl"

sys.path.insert(0, str(SCRIPTS))
import length_policy as lp  # noqa: E402  – SSOT für den Zeichen-Korridor

DRY_RUN = "--dry-run" in sys.argv
AS_JSON = "--json" in sys.argv
NEW_ONLY = "--new-only" in sys.argv
SELFTEST_ONLY = "--selftest" in sys.argv
SEED = "--seed-baseline" in sys.argv

# --- Schwellen (bewusst konservativ, damit nur echte Zerfaserung auffällt)
MIKRO_WORDS = 90      # S1: H2-Abschnitt gilt darunter als Mikro-Abschnitt
SERIE_MIN = 3         # S2: ab so vielen gleich beginnenden H2 in Folge
NEU_TOLERANZ = 2      # neue Artikel dürfen so viele Mikro-Abschnitte haben

# Kurze Rubriken mit legitimer Kürze (Kanon des Hauses).
EXEMPT_RX = re.compile(
    r"^(das wichtigste in k|kurzantwort|auf einen blick|inhalt|"
    r"quellen|transparenz|über (den|die) autor|h(ä|ae)ufige fragen|"
    r"faq|weiterlesen|fazit)",
    re.I,
)

RE_CODE = re.compile(r"```.*?```", re.S)
RE_IMG = re.compile(r"!\[[^\]]*\]\([^)]*\)")
RE_HTML = re.compile(r"<[^>]+>")
RE_LINK = re.compile(r"\[([^\]]*)\]\([^)]*\)")


# ---------------------------------------------------------------- Analyse

def split_body(text: str) -> str:
    """Fließtext ohne Front-Matter (gleiche Naht wie check_length.py)."""
    parts = text.split("---", 2)
    return parts[2] if len(parts) >= 3 else text


def _prose_words(block: str) -> int:
    """Wörter eines Abschnitts ohne Überschrift, Code, Bilder, Tabellen-
    Gerüst und CTA-Zitatzeilen – gezählt wird, was der Leser als Text
    wahrnimmt."""
    lines = []
    for line in block.splitlines():
        s = line.strip()
        if s.startswith("#"):
            continue
        if s.startswith("|") or set(s) <= set("-|: "):
            continue
        lines.append(line)
    t = "\n".join(lines)
    t = RE_CODE.sub(" ", t)
    t = RE_IMG.sub(" ", t)
    t = RE_HTML.sub(" ", t)
    t = RE_LINK.sub(r"\1", t)
    t = re.sub(r"[|#*>\[\]()_]", " ", t)
    return len([w for w in t.split() if any(c.isalnum() for c in w)])


def sections(body: str) -> list[tuple[str, int]]:
    """(Überschrift, Wörter) je H2-Abschnitt – Reihenfolge wie im Artikel."""
    out: list[tuple[str, int]] = []
    cur_head: str | None = None
    cur: list[str] = []
    for line in body.splitlines():
        if re.match(r"^##(?!#)\s+", line):
            if cur_head is not None:
                out.append((cur_head, _prose_words("\n".join(cur))))
            cur_head = re.sub(r"^##\s+", "", line).strip()
            cur = []
        elif cur_head is not None:
            cur.append(line)
    if cur_head is not None:
        out.append((cur_head, _prose_words("\n".join(cur))))
    return out


def mikro_abschnitte(secs: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """S1: zu dünne H2-Abschnitte (Kanon-Rubriken ausgenommen)."""
    return [(h, w) for h, w in secs
            if w < MIKRO_WORDS and not EXEMPT_RX.match(h)]


def _erstwort(head: str) -> str:
    m = re.match(r"[A-Za-zÄÖÜäöüß]+", head.strip())
    return m.group(0).lower() if m else ""


def serien(secs: list[tuple[str, int]]) -> list[tuple[str, int]]:
    """S2: Läufe von >= SERIE_MIN AUFEINANDERFOLGENDEN H2, die mit demselben
    Wort beginnen UND allesamt Mikro-Abschnitte sind.

    Die Mikro-Bedingung ist entscheidend: „Trick 1 … Trick 4“ mit je 150+
    Wörtern ist gute redaktionelle Dramaturgie und darf nie als Fund gelten.
    Der Schaden aus #476 sah anders aus – „Welche … / Welche … / Welche …“
    mit je 40–70 Wörtern, angehängt in Serie.

    Rückgabe: (Anfangswort, Länge des Laufs).
    """
    treffer: list[tuple[str, int]] = []
    lauf_wort, lauf_len = "", 0
    for head, w_count in list(secs) + [("", 0)]:
        w = _erstwort(head)
        duenn = w_count < MIKRO_WORDS and not EXEMPT_RX.match(head)
        if w and w == lauf_wort and duenn:
            lauf_len += 1
            continue
        if lauf_len >= SERIE_MIN:
            treffer.append((lauf_wort, lauf_len))
        lauf_wort, lauf_len = (w, 1) if (w and duenn) else ("", 0)
    return treffer


def analyse(text: str) -> dict:
    body = split_body(text)
    secs = sections(body)
    mikro = mikro_abschnitte(secs)
    ser = serien(secs)
    _words, chars = lp.measure(text)
    return {
        "h2": len(secs),
        "chars": chars,
        "mikro": len(mikro),
        "mikro_titel": [h for h, _ in mikro],
        "serien": len(ser),
        "serien_detail": [f"{w}… ×{n}" for w, n in ser],
        # S3: Zerfaserung, die zusätzlich den Optimum-Korridor sprengt.
        "ueberlang": chars > lp.POSTS["opt_max_chars"] and bool(mikro),
    }


# ---------------------------------------------------------------- Bestand

def post_paths(new_only: bool = False) -> list[Path]:
    if not POSTS_DIR.is_dir():
        return []
    paths = sorted(p / "index.md" for p in POSTS_DIR.iterdir()
                   if (p / "index.md").is_file())
    if not new_only:
        return paths
    heute = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return [p for p in paths if p.parent.name.startswith(heute)]


def load_baseline() -> dict:
    if not BASELINE.is_file():
        return {}
    try:
        data = json.loads(BASELINE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data.get("artikel", {}) if isinstance(data, dict) else {}


def bewerte(slug: str, ist: dict, base: dict | None) -> list[str]:
    """Sperrklinke: Zuwachs meldet, Rückgang ist willkommen."""
    funde = []
    if base is None:
        if ist["mikro"] > NEU_TOLERANZ:
            funde.append(
                f"S1 neuer Artikel startet mit {ist['mikro']} Mikro-Abschnitten "
                f"(< {MIKRO_WORDS} Wörter, erlaubt sind {NEU_TOLERANZ})")
        if ist["serien"]:
            funde.append(f"S2 Serien-Überschriften: {', '.join(ist['serien_detail'])}")
        return funde
    if ist["mikro"] > base.get("mikro", 0):
        funde.append(
            f"S1 Mikro-Abschnitte gewachsen: {base.get('mikro', 0)} → {ist['mikro']} "
            f"(angehängte Mini-Rubriken statt Textverdichtung)")
    if ist["serien"] > base.get("serien", 0):
        funde.append(
            f"S2 Serien-Überschriften gewachsen: {base.get('serien', 0)} → "
            f"{ist['serien']} ({', '.join(ist['serien_detail'])})")
    if ist["ueberlang"] and not base.get("ueberlang", False):
        funde.append(
            f"S3 Zerfaserung mit Überlänge: {ist['chars']} Zeichen über dem "
            f"Optimum ({lp.POSTS['opt_max_chars']}) bei {ist['mikro']} "
            f"Mikro-Abschnitten – vor dem harten Deckel "
            f"({lp.POSTS['fat_chars']}) eingreifen")
    return funde


# ---------------------------------------------------------------- Selbsttest

def _selftest() -> list[str]:
    fehler: list[str] = []
    kurz = "Ein kurzer Satz mit wenigen Wörtern.\n"
    lang = ("Dieser Abschnitt trägt echten Inhalt. " * 30)

    fm = "---\ntitle: \"T\"\n---\n\n"
    art = fm + f"## Voller Abschnitt\n\n{lang}\n\n## Welche Frage hilft\n\n{kurz}\n"
    r = analyse(art)
    if r["h2"] != 2:
        fehler.append(f"Fall 1: H2-Zählung {r['h2']} statt 2")
    if r["mikro"] != 1 or r["mikro_titel"] != ["Welche Frage hilft"]:
        fehler.append(f"Fall 1: Mikro-Erkennung falsch ({r['mikro_titel']})")

    # Fall 2: Kanon-Rubriken sind befreit (kurz ist dort legitim).
    art2 = fm + f"## Das Wichtigste in Kürze\n\n- Punkt eins\n- Punkt zwei\n\n## Fazit\n\n{kurz}\n"
    if analyse(art2)["mikro"] != 0:
        fehler.append("Fall 2: Kanon-Rubrik fälschlich als Mikro-Abschnitt gewertet")

    # Fall 3: Serien-Signatur (der Fingerabdruck aus #476).
    art3 = fm + "".join(
        f"## Welche Sache {i} hilft\n\n{kurz}\n" for i in range(3))
    r3 = analyse(art3)
    if r3["serien"] != 1 or not r3["serien_detail"][0].startswith("welche"):
        fehler.append(f"Fall 3: Serien-Signatur nicht erkannt ({r3['serien_detail']})")

    # Fall 4a: zwei gleich beginnende Mini-Abschnitte sind noch keine Serie.
    art4 = fm + "".join(f"## Welche Sache {i}\n\n{kurz}\n" for i in range(2))
    if analyse(art4)["serien"] != 0:
        fehler.append("Fall 4a: zwei Überschriften fälschlich als Serie gewertet")

    # Fall 4b: „Trick 1 … Trick 4“ mit echtem Inhalt ist Dramaturgie,
    # kein Schaden – eine Serie VOLLER Abschnitte darf nie anschlagen.
    art4b = fm + "".join(f"## Trick {i}: Der Hebel\n\n{lang}\n" for i in range(1, 5))
    r4b = analyse(art4b)
    if r4b["serien"] != 0 or r4b["mikro"] != 0:
        fehler.append("Fall 4b: inhaltsstarke Serie („Trick 1–4“) fälschlich gemeldet")

    # Fall 5: Tabellenzeilen zählen nicht als Fließtext.
    tab = "| a | b |\n| :--- | :--- |\n" + "".join(f"| Zeile {i} | Wert |\n" for i in range(20))
    if analyse(fm + f"## Tabellen-Abschnitt\n\n{tab}\n")["mikro"] != 1:
        fehler.append("Fall 5: Tabellen-Gerüst wurde als Fließtext gezählt")

    # Fall 6: Sperrklinke – Zuwachs meldet, Rückgang nicht.
    ist = {"mikro": 4, "serien": 1, "serien_detail": ["welche… ×3"],
           "ueberlang": False, "chars": 15000}
    if not bewerte("x", ist, {"mikro": 3, "serien": 1, "ueberlang": False}):
        fehler.append("Fall 6: Zuwachs an Mikro-Abschnitten nicht gemeldet")
    if bewerte("x", ist, {"mikro": 9, "serien": 4, "ueberlang": True}):
        fehler.append("Fall 6: Rückgang fälschlich gemeldet (Klinke blockiert Heilung)")

    # Fall 7: neuer Artikel innerhalb der Toleranz bleibt still.
    neu = {"mikro": NEU_TOLERANZ, "serien": 0, "serien_detail": [],
           "ueberlang": False, "chars": 14000}
    if bewerte("neu", neu, None):
        fehler.append("Fall 7: Neu-Artikel in Toleranz fälschlich gemeldet")

    # Fall 8: S3 greift VOR dem harten Deckel.
    if lp.POSTS["opt_max_chars"] >= lp.POSTS["fat_chars"]:
        fehler.append("Fall 8: Korridor unplausibel (Optimum >= Deckel)")
    return fehler


# ---------------------------------------------------------------- Bericht

def schreibe_bericht(zeilen: list[str]) -> None:
    if DRY_RUN:
        return
    REPORT.write_text("\n".join(zeilen) + "\n", encoding="utf-8")


def schreibe_baseline(stand: dict) -> None:
    """Schreibt NUR, wenn sich der Artikel-Stand wirklich geändert hat.

    Sonst würde jeder Lauf allein durch das Datumsfeld eine Dateiänderung
    erzeugen – und die Arbeitsbaum-Wachen der Workflows (C15) meldeten
    Rauschen statt Befunde.
    """
    if DRY_RUN:
        return
    if load_baseline() == stand and BASELINE.is_file():
        return
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(json.dumps({
        "hinweis": ("Sperrklinke des Struktur-Guards: je Artikel der akzeptierte "
                    "Stand an Mikro-Abschnitten/Serien. Werte dürfen nur kleiner "
                    "werden – Zuwachs ist ein Fund (scripts/struktur_guard.py)."),
        "stand": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "schwellen": {"mikro_words": MIKRO_WORDS, "serie_min": SERIE_MIN,
                      "neu_toleranz": NEU_TOLERANZ},
        "artikel": stand,
    }, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def schreibe_history(funde: int, geprueft: int, geklinkt: int) -> None:
    if DRY_RUN:
        return
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({
            "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "geprueft": geprueft,
            "funde": funde,
            "geklinkt": geklinkt,
        }, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------- Hauptlauf

def main() -> int:
    fehler = _selftest()
    if fehler:
        print("❌ Struktur-Guard Selbsttest ROT – nichts geprüft, nichts geschrieben:")
        for f in fehler:
            print(f"   · {f}")
        return 2
    if SELFTEST_ONLY:
        print("✅ Struktur-Guard Selbsttest grün (9 eingefrorene Fälle).")
        return 0

    baseline = load_baseline()
    stand: dict[str, dict] = {}
    funde: list[tuple[str, list[str]]] = []
    geklinkt = 0
    paths = post_paths(NEW_ONLY)

    for path in paths:
        slug = path.parent.name
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        ist = analyse(text)
        base = baseline.get(slug)
        neue_funde = bewerte(slug, ist, base)
        if neue_funde:
            funde.append((slug, neue_funde))
        # Klinke: der neue Stand ist nie schlechter als der alte.
        if base is not None and (ist["mikro"] < base.get("mikro", 0)
                                 or ist["serien"] < base.get("serien", 0)):
            geklinkt += 1
        stand[slug] = {
            "mikro": min(ist["mikro"], base["mikro"]) if base else ist["mikro"],
            "serien": min(ist["serien"], base["serien"]) if base else ist["serien"],
            "ueberlang": ist["ueberlang"] and (base or {}).get("ueberlang", ist["ueberlang"]),
        }

    # Bei --new-only bleibt der übrige Bestand in der Baseline unangetastet.
    if NEW_ONLY:
        merged = dict(baseline)
        merged.update(stand)
        stand = merged

    if SEED:
        schreibe_baseline(stand)
        print(f"🔒 Baseline eingefroren: {len(stand)} Artikel → {BASELINE.relative_to(ROOT)}")
        return 0

    schreibe_baseline(stand)

    zeilen = [
        "# 🧱 STRUKTUR-REPORT (struktur_guard.py)",
        "",
        f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · "
        f"**geprüft:** {len(paths)} Artikel · **Funde:** {len(funde)} · "
        f"**Klinke eingerastet:** {geklinkt}",
        "",
        f"**Schwellen:** Mikro-Abschnitt < {MIKRO_WORDS} Wörter · "
        f"Serie ab {SERIE_MIN} gleich beginnenden H2 · "
        f"Optimum bis {lp.POSTS['opt_max_chars']} Zeichen "
        f"(harter Deckel {lp.POSTS['fat_chars']})",
        "",
    ]
    if funde:
        zeilen.append("## ❌ Struktur-Regressionen")
        zeilen.append("")
        for slug, msgs in funde:
            zeilen.append(f"### {slug}")
            zeilen.extend(f"- {m}" for m in msgs)
            zeilen.append("")
    else:
        zeilen.append("🎉 Keine Struktur-Regression – der Bestand zerfasert nicht.")
        zeilen.append("")
    zeilen.append("---")
    zeilen.append("_S1 Mikro-Abschnitte · S2 Serien-Überschriften · S3 Zerfaserung mit "
                  "Überlänge · Sperrklinke: `data/struktur_baseline.json` (nur abwärts). "
                  "Kein Auto-Fix: Abschnitte zusammenführen ist redaktionelle Arbeit._")
    schreibe_bericht(zeilen)
    schreibe_history(len(funde), len(paths), geklinkt)

    if AS_JSON:
        print(json.dumps({"geprueft": len(paths), "funde":
                          [{"slug": s, "meldungen": m} for s, m in funde],
                          "geklinkt": geklinkt}, ensure_ascii=False, indent=2))
    else:
        print(f"Struktur-Guard: {len(paths)} Artikel · {len(funde)} Regression(en) · "
              f"Klinke {geklinkt}×")
        for slug, msgs in funde:
            for m in msgs:
                print(f"  ❌ {slug}: {m}")
        if not funde:
            print("🎉 Keine Zerfaserung – Struktur auf Premium-Niveau.")
    return 1 if funde else 0


if __name__ == "__main__":
    sys.exit(main())
