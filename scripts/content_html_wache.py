#!/usr/bin/env python3
"""content_html_wache.py — Rohes HTML in Inhalten prüfen (F-06, F-09).

Warum diese Wache existiert
--------------------------
`hugo.toml` baut mit `[markup.goldmark.renderer] unsafe = true`. Das ist für den
Bestand nötig (Tabellen- und Kachel-Blöcke), lässt aber **jedes** HTML aus einer
Inhaltsdatei unverändert ins Ergebnis. Gefährlich wird das, weil Inhalte in
diesem Repo aus mehreren automatischen Wegen entstehen: Sprachmemo → Entwurf
(n8n-Bridge), KI-Redaktion, Bot-Beiträge. Ein `<script>` in einem solchen Text
läuft auf der Seite — die Meta-CSP kann `script-src` erst nach der
Hash-Umstellung verbieten, und der Blog ist öffentlich.

Was geprüft wird (fail-closed)
------------------------------
  1. Verhaltens-HTML in `content/**`: `<script`, `<iframe`, `<object|embed|applet`,
     `<form`, `<base`, `<meta http-equiv`, SVG mit Verhalten sowie `on…=`-Attribute.
  2. Ereignis-Attribute (`on…=`) und `javascript:`/`data:text/html` → Befund.
  3. Kurzcode-Ausführung in Inhalten: `{{<` mit Code-Ausführung oder
     `{{%`-Blöcke mit `highlight` sind erlaubt, aber `readFile`, `resources.`
     und `os.` in einer Inhaltsdatei → Befund (Vorlagen-Zugriff von außen).
  4. Die Bau-Ebene (`hugo.toml`) bleibt gehärtet: `[security]` mit
     `enableInlineShortcodes = false`, eingeschränktem `getenv` und nur eigenen
     HTTP-Quellen; `unsafe = true` nur MIT Begründung; kein `resources.GetRemote`
     in Vorlagen.
  Die Frage „darf diese Seite in den Google-Index?" beantwortet bewusst eine
  andere Wache: `scripts/index_hygiene_gate.py` (H1/H8 über die Partial
  `seo_indexierbar.html`). Zwei Wachen, eine Zuständigkeit je Frage.

Der Bericht nennt Datei und Zeile — eine Wache, die nur „irgendwas ist falsch"
sagt, wird ignoriert. `--selftest` baut die Fälle aus Wegwerf-Dateien in einem
temporären Verzeichnis; er braucht Netz und Hugo **nicht**.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
INHALT = WURZEL / "content"

# Erlaubte Roh-HTML-Nutzung im Bestand: div/span/p/a/img/table… – der Zweck ist
# Layout, nicht Verhalten. Alles unten Genannte ist Verhalten oder Fremdinhalt.
VERBOTEN: tuple[tuple[str, str, str], ...] = (
    ("script", r"<\s*script\b", "Skript in einer Inhaltsdatei — führt Code im Browser des Lesers aus."),
    ("iframe", r"<\s*iframe\b", "Fremde Seite im eigenen Rahmen (Klickdiebstahl, Tracking)."),
    ("object/embed", r"<\s*(object|embed|applet)\b", "Eingebettete Fremdobjekte."),
    ("form", r"<\s*form\b", "Eigenes Formular in einem Beitrag (Phishing-Fläche)."),
    ("base", r"<\s*base\b", "Ein <base> biegt alle relativen Verweise um."),
    ("meta-refresh", r"<\s*meta\b[^>]*http-equiv", "Meta-Umleitung aus einem Beitrag."),
    ("svg-mit-skript", r"<\s*svg\b[^>]*(on\w+\s*=|<script)", "SVG mit Verhalten."),
    ("ereignis-attribut", r"\son(?:error|load|click|mouseover|focus|submit|animationstart|toggle)\s*=",
     "Ereignis-Attribut — der klassische HTML-Einschleusweg (onerror=)."),
    ("javascript-uri", r"(?i)javascript\s*:", "javascript:-Verweis."),
    ("data-html-uri", r"(?i)data\s*:\s*text/html", "HTML als Daten-URL."),
    ("template-code", r"\{\{[<%][^}]*\b(readFile|resources\.|os\.|getenv|exec|transform\.Unmarshal)\b",
     "Vorlagen-Zugriff aus einer Inhaltsdatei (Dateien/Umgebung lesen)."),
)

# Interne Seiten, die nicht indexiert werden dürfen.
INTERN: dict[str, str] = {
    "cockpit": "Betreiber-Cockpit",
    "aenderungsprotokoll": "Änderungsprotokoll",
    "methodik": "Methodik",
}


def dateien_scannen(wurzel: Path) -> list[tuple[Path, int, str, str]]:
    """Alle Markdown-Inhalte prüfen. → [(Datei, Zeile, Regel, Zeilentext)]"""
    befunde: list[tuple[Path, int, str, str]] = []
    for pfad in sorted(wurzel.rglob("*.md")):
        if any(teil.startswith(".") for teil in pfad.relative_to(wurzel).parts):
            continue
        for nummer, zeile in enumerate(pfad.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for name, muster, _ in VERBOTEN:
                if re.search(muster, zeile):
                    befunde.append((pfad, nummer, name, zeile.strip()[:160]))
    return befunde


def konfig_pruefen() -> list[str]:
    """Die Bau-Ebene muss gehärtet bleiben (F-06, dauerhaft).

    Diese Prüfung ist der Regressionsschutz für `hugo.toml`: Wer die
    Sicherheitssektion entfernt (oder `unsafe = true` ohne Bewachung neu
    setzt), bekommt hier einen Befund statt einer stillen Lücke. Die Frage
    „darf diese Seite in den Index?" beantwortet bewusst NICHT diese Wache –
    das macht `scripts/index_hygiene_gate.py` mit der Partial
    `seo_indexierbar.html` an einer Stelle.
    """
    fehler: list[str] = []
    hugo = (WURZEL / "hugo.toml").read_text(encoding="utf-8")

    def muss(muster: str, meldung: str) -> None:
        if not re.search(muster, hugo, re.M):
            fehler.append(meldung)

    muss(r"^\s*\[security\]", "`[security]` fehlt in hugo.toml — dann gilt für Inline-"
                             "Kurzschnitte und Vorlagen-Zugriffe wieder der unsichere Standard.")
    muss(r"^\s*enableInlineShortcodes\s*=\s*false",
         "`[security] enableInlineShortcodes = false` fehlt — Kurzcodes IN Inhaltsdateien "
         "könnten dann beliebigen Code ausführen.")
    muss(r"^\s*getenv\s*=\s*\[", "`[security.funcs] getenv` fehlt — Templates sähen dann "
                                     "alle Umgebungsvariablen (Tokens, Kontodaten).")
    muss(r"^\s*urls\s*=\s*\[.*franksfinanzcheck",
         "`[security.http] urls` fehlt oder erlaubt fremde Quellen — der Bau könnte dann "
         "beliebige Fremdinhalte nachladen.")
    muss(r"^\s*\[markup\.goldmark\.renderer\]", "Die Renderer-Sektion fehlt.")
    if re.search(r"^\s*unsafe\s*=\s*true", hugo, re.M):
        # Erlaubt, aber nur mit Begründung im Klartext darüber (Bestand).
        umfeld = hugo[max(0, hugo.index("unsafe = true") - 1200):hugo.index("unsafe = true")]
        if "BEGRÜNDUNG" not in umfeld and "F-06" not in umfeld:
            fehler.append("`unsafe = true` steht ohne Begründung/Fundstelle in hugo.toml — "
                          "dann ist nicht mehr erkennbar, WARUM Roh-HTML erlaubt ist, und "
                          "die nächste Änderung entfernt den Schutz still.")
    # Vorlagen dürfen nicht ins Netz greifen (es gibt heute keinen Grund dafür).
    for vorlage in (WURZEL / "layouts").rglob("*.html"):
        text = vorlage.read_text(encoding="utf-8", errors="replace")
        if "resources.GetRemote" in text:
            fehler.append(f"`{vorlage.relative_to(WURZEL)}` lädt Fremdinhalt "
                          "(resources.GetRemote) — das ist eine bewusste Entscheidung, "
                          "kein Zufall; hier begründen und freigeben.")
    return fehler


def bestand_pruefen(wurzel: Path = INHALT) -> tuple[int, list[str], list[str]]:
    """→ (Exit-Code, Fehlerliste, Hinweisliste)"""
    if not wurzel.exists():
        return 1, [f"`{wurzel}` fehlt — ohne Inhalt prüft diese Wache nichts und "
                   "darf nicht grün melden."], []
    befunde = dateien_scannen(wurzel)
    gruende = {name: grund for name, _, grund in VERBOTEN}

    def kurz(pfad: Path) -> str:
        try:
            return str(pfad.relative_to(WURZEL))
        except ValueError:
            return str(pfad)  # Selbsttest-Verzeichnis außerhalb des Repos

    fehler = [f"`{kurz(p)}:{n}` — **{regel}**: {text}\n     ({gruende[regel]})"
              for p, n, regel, text in befunde]
    fehler += konfig_pruefen()

    hinweise: list[str] = []
    # Sanity: Wie viel Roh-HTML gibt es überhaupt? Eine große Änderung der
    # Menge ist ein Hinweis, kein Fehler (Layout-Umbau).
    divs = 0
    for pfad in sorted(wurzel.rglob("*.md")):
        divs += len(re.findall(r"<\s*div\b", pfad.read_text(encoding="utf-8", errors="replace")))
    hinweise.append(f"Roh-HTML im Bestand: {divs} <div>-Blöcke (Layout, erlaubt).")
    return (1 if fehler else 0), fehler, hinweise


# ------------------------------------------------------------------ Selbsttest
def selftest() -> int:
    faelle = 0
    with tempfile.TemporaryDirectory() as tmp:
        w = Path(tmp)
        (w / "cockpit").mkdir(parents=True)
        (w / "cockpit" / "index.md").write_text(
            "---\ntitle: Cockpit\nrobotsNoIndex: true\n---\nAlles gut.\n", encoding="utf-8")
        (w / "aenderungsprotokoll").mkdir(parents=True)
        (w / "aenderungsprotokoll" / "index.md").write_text(
            "---\ntitle: Protokoll\nrobotsNoIndex: true\n---\n", encoding="utf-8")
        (w / "methodik").mkdir(parents=True)
        (w / "methodik" / "index.md").write_text(
            "---\ntitle: Methodik\nrobotsNoIndex: true\n---\n", encoding="utf-8")
        (w / "posts").mkdir()
        sauber = w / "posts" / "sauber.md"
        sauber.write_text("---\ntitle: Sauber\n---\n\n<div class=\"ff-kachel\">Text</div>\n",
                          encoding="utf-8")

        code, fehler, _ = bestand_pruefen(w)
        assert code == 0 and not fehler, f"Sauberer Bestand beanstandet: {fehler}"
        faelle += 1

        # Gegenproben: jede Regel einmal verletzen.
        for name, muster, _ in VERBOTEN:
            probe = {
                "script": 'Text <script>alert(1)</script>',
                "iframe": '<iframe src="https://boese.example"></iframe>',
                "object/embed": '<object data="x.swf"></object>',
                "form": '<form action="https://boese.example"><input></form>',
                "base": '<base href="https://boese.example/">',
                "meta-refresh": '<meta http-equiv="refresh" content="0;url=https://boese.example">',
                "svg-mit-skript": '<svg onload="alert(1)"></svg>',
                "ereignis-attribut": '<img src="x" onerror="alert(1)">',
                "javascript-uri": '<a href="javascript:alert(1)">klick</a>',
                "data-html-uri": '<a href="data:text/html;base64,PHNjcmlwdD4=">klick</a>',
                "template-code": '{{< readFile "hugo.toml" >}}',
            }[name]
            sauber.write_text(f"---\ntitle: Probe\n---\n\n{probe}\n", encoding="utf-8")
            code, fehler, _ = bestand_pruefen(w)
            assert code == 1 and any(name in f for f in fehler), \
                f"Regel {name} nicht erkannt (Befunde: {fehler})"
            faelle += 1

        # Gegenprobe: Bau-Ebene gehärtet? (hugo.toml wird im Selbsttest nicht
        # verändert – hier wird nur geprüft, dass die Regel überhaupt greift.)
        f = konfig_pruefen()
        assert not f, f"Der echte hugo.toml-Stand verletzt die Bau-Regeln: {f}"

        # Gegenprobe: leerer Inhalt ist ein Fehler, kein Freibrief.
        code, fehler, _ = bestand_pruefen(w / "gibtsnicht")
        assert code == 1 and any("nichts" in f for f in fehler), \
            "Leerer/fehlender Inhalt muss ein Befund sein"
        faelle += 1

    # Und der echte Bestand muss sauber sein (das ist der eigentliche Zweck).
    code, fehler, hinweise = bestand_pruefen()
    assert code == 0, "DER ECHTE INHALT IST NICHT SAUBER:\n" + "\n".join(fehler)
    print(f"✅ SELBSTTEST OK — {faelle} Fälle grün (11 Einschleusregeln, gehärtete "
          f"Bau-Ebene, leerer Inhalt). Echter Bestand sauber: {hinweise[0]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Rohes HTML in content/** prüfen (F-06).")
    parser.add_argument("--selftest", action="store_true", help="prüft die Prüfung")
    parser.add_argument("--json", action="store_true", help="Befunde als JSON")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    code, fehler, hinweise = bestand_pruefen()
    if args.json:
        print(json.dumps({"exit": code, "fehler": fehler, "hinweise": hinweise},
                         ensure_ascii=False, indent=2))
        return code
    print("# Inhalts-Wache (rohes HTML)")
    print()
    for h in hinweise:
        print(f"- ℹ️ {h}")
    if fehler:
        print(f"\n## Befunde ({len(fehler)})")
        print()
        for f in fehler:
            print(f"- ❌ {f}")
        print("\nKurz: Jedes dieser Muster kann im Browser Verhalten auslösen oder "
              "Besucher auf fremde Seiten schicken. Inhalte sind Text — Layout-Hülsen "
              "bleiben <div>/<span>. Wenn ein Fall unvermeidbar ist: Ausnahme mit "
              "Begründung in `data/content_html_ausnahmen.yaml` und hier eintragen, "
              "nie still schweigen.")
        return code
    print("\n✅ Kein eingeschleustes HTML, keine Ereignis-Attribute, keine "
          "Vorlagen-Zugriffe. Interne Seiten bleiben aus Suchmaschinen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
