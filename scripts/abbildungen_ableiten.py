#!/usr/bin/env python3
"""Eigene Abbildungen für die Top-20-Beiträge (SEO-Punkt 4), reproduzierbar.

Quelle der Auswahl: data/top20_abbildungen.yaml (Regel steht dort).
Je Beitrag entstehen zwei SVG-Dateien im Beitragsordner, abgeleitet nur aus dem
eigenen Text des Beitrags (keine neuen Fakten):
  - abbildung-merkkarte.svg  Kernaussagen aus der Kurzantwort (max. 3 Sätze)
  - abbildung-ablauf.svg     Gliederung aus den Zwischenüberschriften

BILDUNTERSCHRIFTEN SIND ARTIKELSPEZIFISCH (Dauerheilung #824, 24.10.2026)
--------------------------------------------------------------------------
Bis 24.10.2026 schrieb dieses Werkzeug in JEDEN der 20 Beiträge wörtlich
dieselbe Unterschrift:

  *Abbildung: Gliederung des Beitrags in seinen Zwischenüberschriften
   (eigene Darstellung).*

Damit standen 20 Artikel mit einem identischen Absatz im Bestand – die
Duplikat-Wache (D3-X) und das Einzigartigkeits-Audit (U1) meldeten das
korrekt als Redundanz, 25 Live-Artikel standen in der Release-Scorecard
dauerhaft auf „blockiert“ (#824). Die Wache war nicht zu streng, der
Generator war es: Eine Bildunterschrift, die den Artikel nicht beschreibt,
ist auf jeder Seite derselbe Satz.

Deshalb leitet `caption_*()` die Unterschrift aus dem Beitrag selbst ab
(Titel, Kernaussage, Abschnittsnamen). Zwei Beiträge können dadurch keine
gleiche Unterschrift tragen – `--check` beweist das bei jedem Lauf, und
`--selftest` friert es ein. Der Lauf REPARIERT bestehende Altfassungen
(ersetzt die alte Unterschrift), statt sie zu verdoppeln.

Modi:
  python3 scripts/abbildungen_ableiten.py            # erzeugen + einbinden (idempotent, heilt Altfassungen)
  python3 scripts/abbildungen_ableiten.py --check    # Exit 1 bei fehlender/gleicher Unterschrift
  python3 scripts/abbildungen_ableiten.py --selftest # Regelprüfung ohne Dateischreiben
"""
import glob
import html
import os
import re
import sys
import textwrap

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIST_PATH = os.path.join(BLOG_DIR, "data", "top20_abbildungen.yaml")
SKIP = re.compile(
    r"Wichtigste|FAQ|Häufige|Fazit|Weiterrechnen|Passende|Quellen|Fragen|Ausblick|"
    r"Rechner|Themenseite|Affiliate|Transparenz",
    re.I,
)
MERK = "abbildung-merkkarte.svg"
ABLAUF = "abbildung-ablauf.svg"

# Bildzeile und Unterschrift sind getrennte Blöcke: Die Bildzeile trägt den
# Alt-Text (mit Titel), die Unterschrift den beschreibenden Satz. Beide werden
# hier erkannt, damit ein zweiter Lauf die vorhandene Fassung AKTUALISIERT
# statt sie zu verdoppeln.
BILD_RE = {
    MERK: re.compile(r"^!\[[^\]]*\]\(" + re.escape(MERK) + r"\)\s*$"),
    ABLAUF: re.compile(r"^!\[[^\]]*\]\(" + re.escape(ABLAUF) + r"\)\s*$"),
}
UNTERSCHRIFT_RE = re.compile(r"^\*Abbildung:[^\n]*\*\s*$")


def load_slugs():
    """Liest die Liste ohne PyYAML: Zeilen der Form  - slug: "<verzeichnis>"."""
    with open(LIST_PATH, encoding="utf-8") as fh:
        slugs = re.findall(r'^\s*-\s*slug:\s*"([^"]+)"', fh.read(), re.M)
    if not slugs:
        raise SystemExit(f"🛑 keine Beiträge in {LIST_PATH}")
    return slugs


def find_post(slug):
    hits = glob.glob(os.path.join(BLOG_DIR, "content", "posts", slug + "*", "index.md"))
    if len(hits) != 1:
        raise SystemExit(f"🛑 Beitrag nicht eindeutig: {slug} ({len(hits)} Treffer)")
    return hits[0]


def clean(text):
    text = re.sub(r"\*\*|__|\*|`", "", text)
    text = text.replace("‑", "-").replace("&nbsp;", " ").replace("\xa0", " ")
    text = text.replace("&quot;", '"').replace("&amp;", "&")
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text):
    return [
        s.strip()
        for s in re.split(r'(?<!\d)(?<=[.!?])\s+(?=[A-ZÄÖÜ„"])', text)
        if s.strip()
    ]


def merkkarte_svg(title, sentences):
    width, pad, y = 800, 40, 40
    parts = [f'<text x="{pad}" y="{y + 26}" font-size="26" font-weight="700" fill="#1f3a5f">Auf einen Blick</text>']
    y += 50
    parts.append(f'<line x1="{pad}" y1="{y}" x2="{width - pad}" y2="{y}" stroke="#d7e0ea" stroke-width="2"/>')
    y += 28
    for sentence in sentences:
        for i, line in enumerate(textwrap.wrap(sentence, width=62)):
            prefix = "•  " if i == 0 else "    "
            parts.append(f'<text x="{pad}" y="{y + 22}" font-size="21" fill="#222">{html.escape(prefix + line)}</text>')
            y += 32
        y += 12
    height = y + 60
    parts.append(f'<text x="{pad}" y="{height - 24}" font-size="16" fill="#6b7a8c">FranksFinanzcheck · Zusammenfassung des Beitrags</text>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{html.escape("Merkkarte: " + title)}">'
        '<rect width="100%" height="100%" fill="#f6f9fc"/>' + "".join(parts) + "</svg>"
    )


def ablauf_svg(title, steps):
    width, row = 800, 78
    height = 80 + row * len(steps) + 50
    parts = ['<text x="40" y="52" font-size="26" font-weight="700" fill="#1f3a5f">Gliederung des Beitrags</text>']
    for i, step in enumerate(steps):
        top = 90 + i * row
        parts.append(f'<circle cx="70" cy="{top + 22}" r="22" fill="#1f6f5c"/>')
        parts.append(f'<text x="70" y="{top + 29}" font-size="20" font-weight="700" fill="#fff" text-anchor="middle">{i + 1}</text>')
        for j, line in enumerate(textwrap.wrap(step, width=52)[:2]):
            parts.append(f'<text x="110" y="{top + 18 + j * 26}" font-size="21" fill="#222">{html.escape(line)}</text>')
        if i < len(steps) - 1:
            parts.append(f'<line x1="70" y1="{top + 44}" x2="70" y2="{top + row - 2}" stroke="#9fb8cc" stroke-width="3"/>')
    parts.append(f'<text x="40" y="{height - 20}" font-size="16" fill="#6b7a8c">FranksFinanzcheck · Zwischenüberschriften des Beitrags in Reihenfolge</text>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="{html.escape("Gliederung: " + title)}">'
        '<rect width="100%" height="100%" fill="#ffffff"/>' + "".join(parts) + "</svg>"
    )


def build(post_path):
    with open(post_path, encoding="utf-8") as fh:
        text = fh.read()
    front, body = text.split("\n---\n", 1)
    title = clean(re.search(r'^title: "(.*)"', front, re.M).group(1))
    summary = clean(re.search(r'^kurzantwort: "(.*)"', front, re.M).group(1))
    sentences = split_sentences(summary)[:3]
    steps = [clean(m.group(1)) for m in re.finditer(r"^## (.+)$", body, re.M) if not SKIP.search(m.group(1))][:5]
    return title, sentences, steps, front, body


def caption_merkkarte(title, sentences=None):
    """Artikelgenaue Unterschrift der Merkkarte.

    Der Titel macht die Zeile einzigartig; die beiden festen Teile bleiben
    bewusst KURZ (drei Wörter davor, fünf danach). Damit kann über zwei
    Beiträge hinweg nie eine gemeinsame 7-Wort-Phrase entstehen – genau die
    hatte zuletzt 20 Artikel als D3-X/U1 blockiert (#824).

    WARUM KEINE KERNAUSSAGE IM ZITAT: Die `kurzantwort` enthält Zahlen und
    Prozentwerte. Eine Bildzeile ist Metadaten, keine zweite Aussage – sie
    darf keine Beträge in den YMYL-Prüfpfad (`fachpruefung_register.py`)
    einschleusen. Zitate bleiben im Artikeltext, wo sie geprüft werden.
    """
    return (f"*Abbildung: Merkkarte zu „{title}“ (eigene Darstellung aus "
            "diesem Beitrag).*")


def caption_ablauf(title, steps):
    """Artikelgenaue Unterschrift der Gliederung (erste und letzte Station).

    Nennt die Stationen des Beitrags – ein Leser weiß damit vor dem Bild,
    wohin die Reise geht, und zwei Beiträge teilen keine Bildzeile.

    WARUM „STATIONEN“ UND NICHT „ABSCHNITTE“: Die Grafik zeigt die ersten
    fünf inhaltlichen Zwischenüberschriften (`SKIP` blendet Kürz-/
    FAQ-/Fazit-Kapitel aus), nicht zwingend alle Kapitel des Beitrags. Die
    Bildzeile darf deshalb keine Gesamtzahl behaupten – sie beschreibt, was
    im Bild steht.
    """
    if len(steps) >= 2:
        return (f"*Abbildung: Gliederung zu „{title}“ – {len(steps)} "
                f"Stationen von „{steps[0]}“ bis „{steps[-1]}“ "
                "(eigene Darstellung).*")
    return f"*Abbildung: Gliederung zu „{title}“ (eigene Darstellung).*"


def _setze_unterschrift(lines, bild, caption):
    """Bildzeile + Unterschrift setzen bzw. eine Altfassung ersetzen.

    Rückgabe: (lines, gefunden). `gefunden` ist False, wenn die Bildzeile
    fehlt – dann fügt der Aufrufer den ganzen Block ein (Erstlauf).
    """
    muster = BILD_RE[bild]
    for i, line in enumerate(lines):
        if not muster.match(line.strip()):
            continue
        # Die Unterschrift steht direkt unter der Bildzeile; dazwischen darf
        # genau EINE Leerzeile liegen (Hugo rendert sie als <figcaption>).
        j = i + 1
        if j < len(lines) and not lines[j].strip():
            j += 1
        if j < len(lines) and UNTERSCHRIFT_RE.match(lines[j].strip()):
            if lines[j] != caption:
                lines[j] = caption
            return lines, True
        lines[i + 1:i + 1] = ["", caption]
        return lines, True
    return lines, False


def render(post_path, write):
    title, sentences, steps, front, body = build(post_path)
    folder = os.path.dirname(post_path)
    merk_caption = caption_merkkarte(title, sentences)
    ablauf_caption = caption_ablauf(title, steps)
    if write:
        with open(os.path.join(folder, MERK), "w", encoding="utf-8") as fh:
            fh.write(merkkarte_svg(title, sentences))
        with open(os.path.join(folder, ABLAUF), "w", encoding="utf-8") as fh:
            fh.write(ablauf_svg(title, steps))
        lines = body.split("\n")
        lines, hat_merk = _setze_unterschrift(lines, MERK, merk_caption)
        lines, hat_ablauf = _setze_unterschrift(lines, ABLAUF, ablauf_caption)
        if not (hat_merk and hat_ablauf):  # Erstlauf: Blöcke einfügen
            h2 = [i for i, line in enumerate(lines) if line.startswith("## ")]
            if len(h2) < 2:
                raise SystemExit(f"🛑 zu wenige Abschnitte für Abbildungen: {post_path}")
            if not hat_ablauf:
                mid = h2[len(h2) // 2]
                lines[mid:mid] = [f"![Gliederung des Beitrags: {title}]({ABLAUF})",
                                  "", ablauf_caption, ""]
            if not hat_merk:
                first = next(i for i, line in enumerate(lines)
                             if line.startswith("## "))
                lines[first:first] = [f"![Merkkarte: Kernaussagen zu {title}]({MERK})",
                                      "", merk_caption, ""]
        neu = "\n".join(lines)
        if neu != body:
            with open(post_path, "w", encoding="utf-8") as fh:
                fh.write(front + "\n---\n" + neu)
    return len(sentences), len(steps)


def pruefe_post(path, problems, gesehen):
    """Prüft EINEN Beitrag: Einbindung, artikelgenaue und eindeutige Bildzeile.

    Eigene Funktion, damit der Regress-Test sie gegen eine synthetische
    Ablage fahren kann – ein Test am Live-Bestand wäre vom Tagesgeschäft
    abhängig (dieselbe Naht wie bei `duplikat_guard.check_article`).
    """
    slug = os.path.basename(os.path.dirname(path))
    folder = os.path.dirname(path)
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    body = text.split("\n---\n", 1)[1] if "\n---\n" in text else text
    title, sentences, steps, _front, _body = build(path)
    erwartet = {
        MERK: caption_merkkarte(title, sentences),
        ABLAUF: caption_ablauf(title, steps),
    }
    for name in (MERK, ABLAUF):
        if not os.path.isfile(os.path.join(folder, name)):
            problems.append(f"{slug}: Datei fehlt {name}")
        if name not in body:
            problems.append(f"{slug}: nicht eingebunden {name}")
            continue
        if erwartet[name] not in body:
            problems.append(
                f"{slug}: Unterschrift fehlt oder ist nicht artikelgenau "
                f"(erwartet: {erwartet[name][:60]}…)")
            continue
        if erwartet[name] in gesehen:
            problems.append(f"{slug}: Unterschrift identisch mit "
                            f"{gesehen[erwartet[name]]} – Artikel müssen "
                            "sich unterscheiden (#824)")
        else:
            gesehen[erwartet[name]] = slug
    return problems


def check(slugs):
    """Prüft Einbindung UND artikelgenaue Unterschrift (Issue #824).

    Eine fehlende, veraltete oder doppelte Unterschrift ist ein Befund:
    Genau die wörtlich gleiche Bildzeile in 20 Artikeln hat die
    Release-Scorecard 25-mal blockiert.
    """
    problems = []
    gesehen = {}
    for slug in slugs:
        pruefe_post(find_post(slug), problems, gesehen)
    return problems


def selftest():
    sample = "Erster Satz. Zweiter Satz mit 3.5 Prozent. Dritter Satz!"
    parts = split_sentences(sample)
    assert parts == ["Erster Satz.", "Zweiter Satz mit 3.5 Prozent.", "Dritter Satz!"], parts
    assert clean("**fett** &quot;x&quot;") == 'fett "x"'
    assert "<svg" in merkkarte_svg("T", ["A."]) and "<svg" in ablauf_svg("T", ["Schritt"])
    # #824: Zwei Beiträge dürfen nie dieselbe Bildzeile tragen. Der Fall ist
    # eingefroren, weil er zuletzt 20 Artikel blockiert hat.
    a_merk = caption_merkkarte("DSL-Wechselbonus sichern", ["Ein Bonus zählt nur mit dem Effektivpreis."])
    b_merk = caption_merkkarte("Tagesgeld im Vergleich", ["Der Zins gilt nur für Neukunden."])
    a_ablauf = caption_ablauf("DSL-Wechselbonus sichern", ["Kosten", "Tarif", "Wechsel"])
    b_ablauf = caption_ablauf("Tagesgeld im Vergleich", ["Zinsen", "Sicherung", "Fazit"])
    assert a_merk != b_merk and a_ablauf != b_ablauf, "Bildzeilen sind nicht artikelgenau"
    assert "DSL-Wechselbonus" in a_merk, a_merk
    assert "Kosten" in a_ablauf and "Wechsel" in a_ablauf, a_ablauf
    # Bildzeilen sind Metadaten: keine Beträge, keine Prozentwerte – sonst
    # wandern Zahlen in den YMYL-Prüfpfad, die dort niemand geprüft hat.
    for caption in (a_merk, b_merk, a_ablauf, b_ablauf):
        assert not re.search(r"\d[\d.,]*\s?(?:€|Euro|Prozent|%)", caption), caption
    # Altfassung wird erkannt und ersetzt (Migrationspfad statt Doppelung).
    alt = [f"![Merkkarte: Kernaussagen zu T]({MERK})", "",
           "*Abbildung: Merkkarte mit den Kernaussagen (eigene Darstellung aus diesem Beitrag).*"]
    neu, gefunden = _setze_unterschrift(list(alt), MERK, a_merk)
    assert gefunden and neu[2] == a_merk and len(neu) == len(alt), neu
    # Zweiter Lauf ist idempotent.
    nochmal, _ = _setze_unterschrift(list(neu), MERK, a_merk)
    assert nochmal == neu, "Abbildungs-Einbindung ist nicht idempotent"
    print("✅ Abbildungen-Selbsttest bestanden (artikelgenaue Bildzeilen, "
          "Altfassung wird ersetzt, idempotent)")
    return 0


def main(argv):
    if "--selftest" in argv:
        return selftest()
    slugs = load_slugs()
    if "--check" in argv:
        problems = check(slugs)
        for p in problems:
            print("  -", p)
        print(f"Abbildungen-Check: {len(slugs)} Beiträge | Befunde: {len(problems)}")
        return 1 if problems else 0
    for slug in slugs:
        sentences, steps = render(find_post(slug), write=True)
        print(f"  ✔ {slug[:60]}: {sentences} Kernsätze, {steps} Gliederungspunkte")
    print(f"Abbildungen erzeugt für {len(slugs)} Beiträge.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
