#!/usr/bin/env python3
"""
R5-ABSATZ-SPLITTER (Audit 01.09.2026, P0-Punkt 5: „Eine Idee pro Absatz“).

Splittet Fließtext-Absätze mit mehr als 4 Sätzen iterativ an Satzgrenzen,
bis keine harte Absatzhälfte bleibt, ohne Markdown-Links zu zerschneiden und
ohne Abkürzungen (z. B., d. h., u. a., 18.000) als Satzende zu werten.

Verifikation: python3 scripts/textverstaendnis_guard.py --json
  → Anzahl R5-ABSATZ-Funde muss sinken, keine neuen harten Fälle.

Nutzung:
  python3 scripts/r5_absatz_splitter.py            # Vorschau (dry-run, Live-Korpus)
  python3 scripts/r5_absatz_splitter.py --apply    # schreibt (Live-Korpus)
  python3 scripts/r5_absatz_splitter.py --apply --include-drafts
                                                   # auch Entwürfe (Korpus)
  python3 scripts/r5_absatz_splitter.py --apply --file content/posts/<slug>/index.md
                                                   # EIN Artikel (Entwürfe
                                                   # grundsätzlich erlaubt;
                                                   # die Reserve-Veredelung
                                                   # fasst so keinen
                                                   # Fremdartikel an)
  python3 scripts/r5_absatz_splitter.py --selftest # Sabotage-Schutz

REPARATUR 11.09.2026 (Reserve #5, Workflow #247):
  * Der Splitter war in KEINEM Workflow verdrahtet – frische
    Reserve-Kandidaten scheiterten dauerhaft am harten R5-ABSATZ-HART-Gate
    (>6 Sätze/Absatz) der Publish-Gate-Prüfung. Er läuft jetzt
    datei-bezirkelt in der Reserve-Heiler-Kette (reserve_finisher.py).
  * --file + --include-drafts für sicheren Entwurfs-Scope.
  * Mehrfach vorkommende Absätze crashten vorher mit einer Assertion
    („Mehrfachfund“) und blockierten den ganzen Lauf; sie werden jetzt
    übersprungen und gemeldet.
  * --selftest als Sabotage-Schutz wie bei den anderen Heilern.
"""
import argparse
import os
import re
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from post_utils import join_article  # noqa: E402  – Naht-SSOT (FM-Grenze)

APPLY = "--apply" in sys.argv
MAX_SENT = 4

# Abkürzungen, deren Punkt kein Satzende ist (werden geschützt)
ABBR = re.compile(r'\b(z\.\s?b\.|d\.\s?h\.|u\.\s?a\.|etc\.|usw\.|bzw\.|inkl\.|ggf\.|ca\.|Nr\.|S\.|Abs\.|Mio\.|Mrd\.|vgl\.|St\.)\b', re.I)

def protect(text: str) -> tuple[str, list[str]]:
    tokens: list[str] = []
    def repl(m: re.Match) -> str:
        tokens.append(m.group(0))
        return f"\x00{len(tokens)-1}\x00"
    return ABBR.sub(repl, text), tokens

def restore(text: str, tokens: list[str]) -> str:
    def repl(m: re.Match) -> str:
        return tokens[int(m.group(1))]
    return re.sub(r'\x00(\d+)\x00', repl, text)

# ---------------------------------------------------------------------------
#  ORDINAL-DATUM: SCHÜTZEN, NICHT LÖSCHEN (Dauerheilung 29.10.2026, WF-D4E0)
# ---------------------------------------------------------------------------
#  Bis hierher „schützte“ der Splitter den Datumspunkt, indem er ihn
#  WEGSCHRIEB:
#      re.sub(r'(\b\d{1,2})\.\s+([A-ZÄÖÜ][a-zäöüß]{2,}\b)', r'\1 \2', p)
#  Aus „am 23. Dezember“ wurde im Zähltext „23 Dezember“ – und weil die
#  Teilung anschließend aus GENAU diesem Text gebaut wurde, landete die
#  Ruine im Artikel: R13-DATUM-PUNKT, ein HARTES Publish-Kriterium (#482).
#  Reale Folge im Nachtlauf 28.10.2026 (Issue #884, Kandidat
#  `2026-10-28-flugvergleich-…`): Der R5-Split der Stufe 2, der den Artikel
#  verlängern sollte, führte R13 ein → Schritt-Vertrag (V2) rollte den Split
#  zurück → die Datei blieb ungeteilt → die Zertifizierungs-Vorheilung teilte
#  erneut (ohne Vertrag) → R13 im Messbild → Gate lehnt ab → Bytes werden
#  zurückgestellt → nächste Nacht dasselbe. Ein Selbstläufer ohne Verlierer
#  außer dem Vorrat: 3/6, seit dem 26.10. jeden Tag.
#  Die Lösung ist deshalb keine Ausnahme, sondern die richtige Technik:
#  Der Punkt wird für die Satzzählung MASKIERT (`\x01` ist kein Satzzeichen
#  und kein Whitespace) und nach der Teilung BYTEGENAU zurückgeschrieben.
#  Damit zählt „23. Dezember“ nicht als Satzende und bleibt trotzdem exakt
#  das, was im Original stand – inklusive schmalem geschütztem Leerzeichen
#  (U+202F), das `\s+` mitnimmt.
MONATE = ("Januar|Februar|März|April|Mai|Juni|Juli|August|September|"
          "Oktober|November|Dezember")
DATUM_PUNKT = re.compile(
    r'(?P<zahl>\b\d{1,2})\.(?P<raum>\s+)(?=(?:' + MONATE + r')\b)')
DATUM_MASKE = "\x01"


def datum_maskieren(text: str) -> str:
    """Ordinal-Punkte für die Satzzählung maskieren – verlustfrei."""
    return DATUM_PUNKT.sub(
        lambda m: m.group('zahl') + DATUM_MASKE + m.group('raum'), text)


def datum_wiederherstellen(text: str) -> str:
    return text.replace(DATUM_MASKE, ".")


def split_para(para: str) -> str | None:
    """Teilt para an einer sinnvollen Satzgrenze. Gibt None, wenn nicht nötig."""
    p, tokens = protect(para)
    # Datumspunkte schützen (maskieren statt löschen – s. o.)
    p = datum_maskieren(p)
    # Satzenden finden (inkl. schließender Klammer/Quote, danach Großbuchstabe/Zahl/Anführung)
    ends = [m.end() for m in re.finditer(r'[.!?][)\"]?\s+(?=[A-ZÄÖÜ0-9„"\[])', p)]
    if not ends:
        return None
    n_sents = len(ends) + 1
    if n_sents <= MAX_SENT:
        return None
    # Bruchstelle so wählen, dass BEIDE Hälften möglichst ≤4 Sätze haben:
    # 5 Sätze → 2+3, 6 → 2+4, 7 → 3+4, 8+ → 4+(n-4). Die alte feste 2+3-Regel
    # ließ bei 7+ Sätzen eine zu lange zweite Hälfte zurück (Reserve #5).
    k = min(max(2, n_sents - MAX_SENT), 4)
    if k < len(ends):
        cut = ends[k - 1]
    else:
        cut = ends[len(ends) // 2]
    a, b = p[:cut], p[cut:]
    a = datum_wiederherstellen(restore(a, tokens))
    b = datum_wiederherstellen(restore(b, tokens))
    # Kein künstlicher Abschluss-Newline: `para` wird in einem Body ersetzt,
    # dessen bestehende Absatztrenner erhalten bleiben. Ein zusätzliches `\n`
    # erzeugte sonst drei Leerzeilen nach jedem Split.
    return a.rstrip() + "\n\n" + b.lstrip()

def paras_with_many_sents(body: str):
    out = []
    for para in body.split("\n\n"):
        s = para.strip()
        if not s or s.startswith(("#", "*", "-", "|", ">", "<", "!", "{", "[")):
            continue
        # nur echte Fließtext-Absätze
        first = s.split("\n", 1)[0]
        if re.match(r'^\s*\d+\.\s', first):
            continue
        p, tokens = protect(s)
        p2 = datum_maskieren(p)
        n = len(re.findall(r'[.!?][)\"]?\s+(?=[A-ZÄÖÜ0-9„"\[])', p2)) + 1
        if n > MAX_SENT:
            out.append((s, n))
    return out


def is_draft(text: str) -> bool:
    parts = text.split("---", 2)
    return len(parts) >= 3 and bool(
        re.search(r"(?m)^draft:\s*true\s*$", parts[1]))


def split_body_text(body: str, max_rounds: int = 6, *, verbose: bool = False,
                    label: str = "") -> tuple[str, int, list[str]]:
    """Splittet einen Markdown-Body in-memory.

    Gemeinsamer Kern für Workflow-Heiler, Publish-Gate und Re-Queue-
    Selbstheilung. So gibt es nur eine R5-Reparaturlogik: keine Gate-Wache muss
    wieder anfangen, ganze Artikel zu parken, nur weil der CLI-Heiler zwar
    existiert, aber in einem Pfad nicht verdrahtet war.
    """
    new_body = body
    total = 0
    warnings: list[str] = []
    # Iterativ teilen, bis kein Fließabsatz mehr > MAX_SENT Sätze hat:
    # ein einziger Durchlauf würde bei 9+ Sätzen eine zu lange zweite
    # Hälfte zurücklassen (Reserve #5, #247). Mehrdeutige Funde werden
    # pro Runde erneut geprüft und im Zweifel konservativ übersprungen.
    for runde in range(max_rounds):
        hits = paras_with_many_sents(new_body)
        if not hits:
            break
        if verbose and runde == 0:
            print(f"\n=== {label or 'Text'} ({len(hits)} Absätze)")
        moved = False
        for para, n in hits:
            if new_body.count(para) != 1:
                # Mehrdeutig (identischer Absatz >1x): keine unsichere Ersetzung.
                msg = f"mehrdeutiger Absatzfund übersprungen: {para[:50]!r}"
                warnings.append(msg)
                if verbose:
                    print(f"  ⚠ {msg}")
                continue
            res = split_para(para)
            if not res:
                continue
            new_body = new_body.replace(para, res, 1)
            total += 1
            moved = True
            if verbose:
                print(f"  [{n} Sätze → aufgeteilt] {para[:60]}…")
        if not moved:
            break
    if new_body != body:
        try:
            import redaktions_standard as rs
            if len(rs._reserve_numeric_claim_findings(new_body)) > len(
                rs._reserve_numeric_claim_findings(body)
            ):
                healed_body, _ = rs.fix_rs4_rs5_deterministic(new_body)
                if len(rs._reserve_numeric_claim_findings(healed_body)) <= len(
                    rs._reserve_numeric_claim_findings(body)
                ):
                    new_body = healed_body
        except Exception:  # noqa: BLE001
            pass
    # FAIL-CLOSED-LETZTLINIE (29.10.2026, WF-D4E0/#884): Eine Teilung darf
    # NIE eine Politur-Ruine (R11–R14, SSOT `sprachkern.POLITUR_RUINEN`)
    # einführen – das sind harte Publish-Kriterien (#482). Die Maskierung
    # oben macht die konkrete Datums-Klasse unerzeugbar; diese Zeile macht
    # die ZUSAGE unabhängig von jeder künftigen Muster-Änderung wahr: Ist
    # die Teilung schlechter als das Original, bleibt das Original stehen
    # und der Grund wird gemeldet (statt still einen Blocker zu bauen).
    if new_body != body:
        try:
            import sprachkern as sk
            neu = set(sk.politur_ruine_funde(new_body))
            alt = set(sk.politur_ruine_funde(body))
            eingefuehrt = sorted(neu - alt)
            if eingefuehrt:
                klassen = ", ".join(f"{regel} {fund!r}"
                                    for regel, fund in eingefuehrt)
                warnings.append(f"R5-Teilung verworfen: sie hätte "
                                f"{klassen} eingeführt (fail-closed)")
                return body, 0, warnings
        except Exception as exc:  # noqa: BLE001 – Wächter nie blockierend
            warnings.append(f"Ruinen-Gegenprobe nicht verfügbar: {exc}")
    return new_body, total, warnings


def heal_text(text: str, *, verbose: bool = False,
              label: str = "") -> tuple[str, int, list[str]]:
    """Splittet den Body einer kompletten Markdown-Datei in-memory.

    Rückgabe: (neuer_text, anzahl_splits, warnungen). Frontmatter bleibt byte-
    nah erhalten; ohne Frontmatter wird der Text unverändert zurückgegeben.
    """
    parts = text.split("---", 2)
    if len(parts) < 3:
        return text, 0, []
    new_body, total, warnings = split_body_text(
        parts[2], verbose=verbose, label=label)
    if new_body == parts[2]:
        return text, total, warnings
    return join_article(parts[1], new_body, parts[0]), total, warnings


def hard_r5_findings(text: str, rel: str = "candidate") -> list:
    """R5-ABSATZ-HART-Funde mit dem echten Textverständnis-Gate messen."""
    try:
        import textverstaendnis_guard as tv
        body = tv.split_body(text)
        return [f for f in tv.check_article(rel, body, {})
                if f[1] == "R5-ABSATZ-HART"]
    except Exception:
        # Fail-safe für Aufrufer: Wenn der Prüfer nicht importierbar ist, soll
        # die Veröffentlichung später am echten Publish-Gate stoppen; dieser
        # Helfer erfindet kein Grün.
        return [(rel, "R5-ABSATZ-HART", "Textverständnisprüfung nicht verfügbar", "")]


def process_file(f: str, apply: bool) -> int:
    """Splittet eine Datei. Rückgabe: Anzahl gesplitteter Absätze."""
    with open(f, encoding="utf-8") as fh:
        t = fh.read()
    new_text, total, _warnings = heal_text(t, verbose=True, label=f)
    if new_text != t and apply:
        with open(f, "w", encoding="utf-8") as fh:
            fh.write(new_text)
    return total


def run_selftest() -> list:
    fehler = []
    # 1) 7-Sätze-Absatz wird in genau 2 Absätze mit <=4 Sätzen geteilt.
    saetze = ("Der erste Gedanke steht hier.", "Ein zweiter Satz folgt direkt.",
              "Dann ein dritter mit Inhalt.", "Ein vierter rundet ab.",
              "Der fünfte beginnt neu.", "Danach der sechste Satz.",
              "Zum Schluss der siebte.")
    para = " ".join(saetze) + "\n"
    res = split_para(para)
    if not res:
        fehler.append("7-Sätze-Absatz wird nicht geteilt")
    else:
        blocks = [b for b in res.strip().split("\n\n") if b.strip()]
        if len(blocks) != 2:
            fehler.append(f"Teilung ergibt {len(blocks)} Absätze statt 2")
        elif any(paras_with_many_sents("\n\n" + b + "\n") for b in blocks):
            fehler.append(f"nach Teilung bleibt ein zu langer Absatz: {blocks}")
    # 2) Kurzer Absatz bleibt unangetastet.
    if split_para("Erster Satz. Zweiter Satz. Dritter Satz.\n") is not None:
        fehler.append("3-Sätze-Absatz wird fälschlich geteilt")
    # 2b) Wiederholte Anwendung löst auch einen 11-Sätze-Absatz vollständig
    # auf (jede resultierende Hälfte muss am Ende <=4 Sätze haben).
    lang_sätze = [
        "Am Anfang steht ein klarer Gedanke.", "Danach folgt ein zweiter Punkt.",
        "Dann kommt ein dritter Aspekt hinzu.", "Ein vierter rundet das Bild ab.",
        "Der fünfte schlägt eine Brücke.", "Auch der sechste hat Gewicht.",
        "Der siebte vertieft das Thema.", "Ein achter Blickwinkel hilft zusätzlich.",
        "Weitere Beobachtungen untermauern den Befund.",
        "Offene Fragen klären sich so von selbst.", "Am Ende bleibt ein Fazit.",
    ]
    lang = " ".join(lang_sätze)
    bloecke = [lang]
    bewegungen = 0
    for _ in range(6):
        neue = []
        bewegt = False
        for b in bloecke:
            r = split_para(b + "\n")
            if r:
                neue.extend(x.strip() for x in r.strip().split("\n\n") if x.strip())
                bewegt = True
                bewegungen += 1
            else:
                neue.append(b.strip())
        bloecke = neue
        if not bewegt:
            break
    if any(paras_with_many_sents("\n\n" + b + "\n") for b in bloecke):
        fehler.append(f"11-Sätze-Absatz konvergiert nicht: {bloecke}")
    # 3) Listen/Überschriften/Tabellen sind keine Fließabsätze.
    body = ("## Überschrift\n\n* Ein Punkt mit mehreren Wörtern hier.\n\n"
            "| a | b |\n|---|---|\n")
    if paras_with_many_sents(body):
        fehler.append("Listen/Überschriften/Tabellen werden als Fließabsatz gewertet")
    # 4) Abkürzungspunkte sind keine Satzenden.
    para = ("Das ist z. B. ein Test u. a. mit Abkürzungen. Ein zweiter Satz "
            "folgt. Ein dritter Satz hier. Ein vierter Satz dran. Ein "
            "fünfter noch.\n")
    res2 = split_para(para)
    if res2 and "z. B." not in res2:
        fehler.append("Abkürzungen wurden beim Teilen zerstört")
    # 5) ORDINAL-DATUM BLEIBT BYTEGENAU (WF-D4E0/#884, 29.10.2026).
    #    Der reale Schaden: „am 23. Dezember“ verlor beim Teilen den Punkt,
    #    wurde als R13-DATUM-PUNKT (hartes Publish-Kriterium) abgelehnt und
    #    hielt den Vorrat Nacht für Nacht bei 3/6.
    datum_para = ("Der erste Gedanke steht hier. Ein zweiter Satz folgt "
                  "direkt. Dann ein dritter mit Inhalt. Fliege zum Beispiel "
                  "am 23.\u202fDezember statt am 24. Dezember. Ein vierter "
                  "rundet ab. Der fünfte beginnt neu. Danach der sechste "
                  "Satz.\n")
    res3 = split_para(datum_para)
    if not res3:
        fehler.append("Absatz mit Ordinal-Datum wird nicht geteilt")
    else:
        if "23.\u202fDezember" not in res3:
            fehler.append("Ordinal-Datum (U+202F) wurde beim Teilen "
                          "verändert – R13-Ruine erzeugt")
        if "24. Dezember" not in res3:
            fehler.append("Ordinal-Datum (ASCII-Leerzeichen) wurde beim "
                          "Teilen verändert – R13-Ruine erzeugt")
    # 5b) Und die Ruinen-Gegenprobe des Kerns hält jede künftige Muster-
    #     Änderung auf: dasselbe Original darf nie schlechter herauskommen.
    try:
        import sprachkern as _sk
        _neu, _n, _warn = split_body_text(datum_para)
        if _sk.politur_ruine_funde(_neu):
            fehler.append(f"Teilung führt eine Politur-Ruine ein: "
                          f"{_sk.politur_ruine_funde(_neu)}")
        if datum_wiederherstellen(datum_maskieren("23. Dezember")) != "23. Dezember":
            fehler.append("Datum-Maske ist nicht verlustfrei")
    except Exception as exc:  # noqa: BLE001
        fehler.append(f"Ruinen-Gegenprobe nicht ausführbar: {exc}")
    return fehler


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="schreibt Dateien")
    ap.add_argument("--file", help="einzelne Datei (Entwürfe erlaubt)")
    ap.add_argument("--include-drafts", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        fehler = run_selftest()
        if fehler:
            print("🛑 R5-ABSATZ-SPLITTER-SELFTEST FEHLGESCHLAGEN:")
            for f in fehler:
                print("   -", f)
            return 2
        print("✅ R5-Absatz-Splitter-Selbsttest grün "
              "(Teilung, Abkürzungen, Scope, Schutzzeilen).")
        return 0

    if args.file:
        files = [args.file]   # --file schließt Entwürfe ausdrücklich ein
    else:
        files = sorted(glob.glob("content/posts/*/index.md"))
        if not args.include_drafts:
            files = [f for f in files
                     if not is_draft(open(f, encoding="utf-8").read())]
    total, changed = 0, []
    for f in files:
        n = process_file(f, args.apply)
        if n:
            total += n
            changed.append(f)
    print(f"\n{total} Absätze gesplittet in {len(changed)} Dateien"
          + (" (geschrieben)" if args.apply else " (dry-run – --apply zum Schreiben)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
