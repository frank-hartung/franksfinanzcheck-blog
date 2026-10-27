#!/usr/bin/env python3
"""Werkzeugbefund-Melder – EIN Meldeweg für kaputte Messwerkzeuge (C38).

WARUM DIESES SKRIPT EXISTIERT (Dauerheilung #740 Teil 2, 14.10.2026)
--------------------------------------------------------------------
Seit #676 gilt im Haus: **erst liefern, dann siegeln.** Ein kaputtes
Messwerkzeug darf die öffentliche Auslieferung nicht als Geisel nehmen; der
Befund gehört NACH der Veröffentlichung in den Job ``release-seal``.

Umgesetzt war dieser Satz zweimal – einmal für die Release-Scorecard (#676)
und einmal für die Quote-Nachfüllung (#740). Beide Male per Hand, beide Male
mit einem eigenen Job-Output (``scorecard_werkzeugfehler``,
``refill_werkzeugfehler``) und einer eigenen ``if``-Zeile im Siegel. Das ist
die Bauweise, die den Befund erzeugt hat, die sie heilen soll: Wer den
nächsten Mess-Schritt baut, müsste denselben Dreiklang erneut von Hand
richtig treffen – Output deklarieren, im Siegel auswerten, im Register
erklären. Vergisst er eine der drei Stellen, meldet niemand etwas (oder,
schlimmer, der Schritt bricht wieder hart ab).

Ab hier gibt es GENAU EINEN Meldeweg:

    python3 scripts/werkzeugbefund.py --melden quote_refill "Messung ausgefallen: hunspell fehlt"

Der Melder schreibt den Befund in eine Lauf-Datei
(``$RUNNER_TEMP/werkzeugbefunde.txt``), setzt die ``::error::``-Annotation
und **endet immer mit Exit 0**. Ein Melder, der am Melden scheitert, ist die
Schadensklasse #227 – deshalb fängt dieses Skript jeden eigenen Fehler ab
und meldet ihn als Text, statt den Schritt zu töten.

Ein einziger Sammler-Schritt vor der Auslieferung macht daraus den
Job-Output ``werkzeugbefunde``; ``release-seal`` färbt den Lauf danach rot.

Nutzung
-------
    --melden <schritt> <text>   Befund anmelden (immer Exit 0)
    --sammeln                   Befunde → GITHUB_OUTPUT/STEP_SUMMARY (immer Exit 0)
    --liste                     Befunde als Klartext (Exit 0; 1 wenn keine)
    --selftest                  Offline-Proben inkl. Sabotage (Exit 0/2)

Die Datei ist über ``WERKZEUGBEFUNDE_DATEI`` umlenkbar – Tests schreiben nie
in ein echtes Lauf-Verzeichnis.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

TRENNER = "\u001f"  # Unit Separator: kann in keinem Schrittnamen vorkommen

try:  # direkter Aufruf: scripts/ liegt auf dem Modulpfad
    from github_kommando import annotation as _melden_anzeige
except ImportError:  # Import als Paket (Tests: from scripts import ...)
    try:
        from scripts.github_kommando import annotation as _melden_anzeige
    except ImportError:  # Notbetrieb: der Melder darf NIE am Melden sterben (#227)
        # Kein Kommando ohne den gemeinsamen Kodierer: Eine ungeprüfte
        # `::`-Zeile könnte ein zweites Kommando erzeugen. Also Klartext.
        def _melden_anzeige(ebene, text, **_):
            print(f"[{ebene}] {text}")
            return False


def befund_datei() -> Path:
    """Lauf-Datei der Werkzeugbefunde (umlenkbar, nie im Repo)."""
    explizit = os.environ.get("WERKZEUGBEFUNDE_DATEI")
    if explizit:
        return Path(explizit)
    basis = os.environ.get("RUNNER_TEMP") or tempfile.gettempdir()
    return Path(basis) / "werkzeugbefunde.txt"


def _eine_zeile(wert: str) -> str:
    """Ein Befund ist EINE Zeile – Umbrüche und Trenner werden entschärft.

    Sabotage-Hintergrund: Ein Zeilenumbruch im Schrittnamen oder im Text
    würde aus einem Befund zwei machen (Geister-Befunde in der Zählung) und
    bei mehrzeiligen Job-Outputs exakt die Delimiter-Kollision aus #227
    auslösen.
    """
    roh = str(wert or "")
    for zeichen in ("\r\n", "\r", "\n", TRENNER, "\t"):
        roh = roh.replace(zeichen, " ")
    return " ".join(roh.split()).strip()


def melden(schritt: str, text: str, *, datei: Path | None = None) -> int:
    """Einen Werkzeugbefund anmelden. Gibt IMMER 0 zurück (#227)."""
    schritt = _eine_zeile(schritt) or "unbenannt"
    text = _eine_zeile(text) or "ohne Meldung"
    ziel = datei or befund_datei()
    zeile = f"{schritt}{TRENNER}{text}"
    try:
        ziel.parent.mkdir(parents=True, exist_ok=True)
        with ziel.open("a", encoding="utf-8") as fh:
            fh.write(zeile + "\n")
    except OSError as exc:  # pragma: no cover - Dateisystem-Notfall
        _melden_anzeige("error", f"Werkzeugbefund konnte nicht abgelegt werden ({exc}) – "
                                 f"Befund trotzdem: {schritt}: {text}")
        return 0
    # Der Melder entscheidet, ob daraus ein Workflow-Kommando wird (WF-E813
    # #815, 27.10.2026): Unter einem Test-Runner bleibt die Zeile Klartext,
    # damit `--selftest` und die Vertragstests keinen Lauf einfärben.
    _melden_anzeige("error", f"{text} "
                             f"Die Auslieferung läuft bewusst weiter; der Lauf wird NACH der "
                             f"Veröffentlichung rot (Job release-seal, Verträge C34/C38). "
                             f"Ausgefallene Messung ist kein Grün (C33).",
                    titel=f"Werkzeugbefund ({schritt})")
    return 0


def lesen(datei: Path | None = None) -> list[tuple[str, str]]:
    """Alle Befunde des Laufs als (Schritt, Text)-Paare."""
    ziel = datei or befund_datei()
    try:
        roh = ziel.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    befunde: list[tuple[str, str]] = []
    for zeile in roh.splitlines():
        if not zeile.strip():
            continue
        schritt, _, text = zeile.partition(TRENNER)
        befunde.append((schritt.strip() or "unbenannt",
                        text.strip() or "ohne Meldung"))
    return befunde


def _anhaengen(pfad: str | None, inhalt: str) -> None:
    if not pfad:
        return
    try:
        with open(pfad, "a", encoding="utf-8") as fh:
            fh.write(inhalt)
    except OSError as exc:  # pragma: no cover - Dateisystem-Notfall
        print(f"⚠ Konnte {pfad} nicht schreiben: {exc}")


def sammeln(datei: Path | None = None) -> int:
    """Befunde → Job-Output + Lauf-Zusammenfassung. Gibt IMMER 0 zurück."""
    befunde = lesen(datei)
    kurz = "; ".join(f"{s}: {t}" for s, t in befunde)
    # Der Output ist einzeilig – mehrzeilige Outputs brauchen Delimiter und
    # sind genau die Fehlerquelle aus #227.
    _anhaengen(os.environ.get("GITHUB_OUTPUT"),
               f"werkzeugbefunde={kurz}\n"
               f"werkzeugbefunde_anzahl={len(befunde)}\n")
    if not befunde:
        print("✅ Keine Werkzeugbefunde in diesem Lauf.")
        return 0
    print(f"🛠 {len(befunde)} Werkzeugbefund(e) für das Siegel eingesammelt:")
    zeilen = ["### 🛠 Werkzeugbefunde (Siegel-Material, C38)", ""]
    for schritt, text in befunde:
        print(f"   - {schritt}: {text}")
        zeilen.append(f"- **{schritt}** – {text}")
    zeilen.append("")
    zeilen.append("_Die Auslieferung lief bewusst weiter (C34). "
                  "Der Lauf wird im Job `release-seal` rot._")
    _anhaengen(os.environ.get("GITHUB_STEP_SUMMARY"), "\n".join(zeilen) + "\n")
    return 0


def _selftest() -> int:
    fehler: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        datei = Path(tmp) / "unter" / "befunde.txt"

        # 1) Melden legt an, auch wenn das Verzeichnis fehlt.
        if melden("quote_refill", "Messung ausgefallen: hunspell", datei=datei) != 0:
            fehler.append("melden() endet nicht mit 0 – ein Melder darf nie töten (#227)")
        if [s for s, _ in lesen(datei)] != ["quote_refill"]:
            fehler.append("Befund wurde nicht abgelegt")

        # 2) Mehrere Befunde bleiben erhalten (append, nicht überschreiben).
        melden("kostensperre", "Geldfläche nicht freigegeben", datei=datei)
        if len(lesen(datei)) != 2:
            fehler.append("Zweiter Befund überschreibt den ersten")

        # 3) Zeilenumbrüche/Trenner dürfen das Format nicht sprengen.
        melden("iso\nlation", f"Text mit{TRENNER}Trenner\nund Umbruch", datei=datei)
        letzte = lesen(datei)[-1]
        if "\n" in letzte[0] or "\n" in letzte[1] or TRENNER in letzte[1]:
            fehler.append("Sabotage: Umbruch/Trenner zerlegt das Befundformat")
        if len(lesen(datei)) != 3:
            fehler.append("Sabotage: Umbruch erzeugt Geister-Befunde")

        # 4) Sammeln schreibt genau EINE Output-Zeile pro Schlüssel.
        out = Path(tmp) / "out.txt"
        summary = Path(tmp) / "summary.md"
        alt_out = os.environ.get("GITHUB_OUTPUT")
        alt_sum = os.environ.get("GITHUB_STEP_SUMMARY")
        os.environ["GITHUB_OUTPUT"] = str(out)
        os.environ["GITHUB_STEP_SUMMARY"] = str(summary)
        try:
            if sammeln(datei) != 0:
                fehler.append("sammeln() endet nicht mit 0 – der Sammler darf nie töten")
            zeilen = out.read_text(encoding="utf-8").splitlines()
            werte = [z for z in zeilen if z.startswith("werkzeugbefunde=")]
            if len(werte) != 1:
                fehler.append(f"Output 'werkzeugbefunde' nicht genau einmal: {zeilen}")
            elif "\n" in werte[0]:
                fehler.append("Output ist mehrzeilig – Delimiter-Falle (#227)")
            if not any(z.startswith("werkzeugbefunde_anzahl=3") for z in zeilen):
                fehler.append(f"Anzahl der Befunde falsch gezählt: {zeilen}")
            if "release-seal" not in summary.read_text(encoding="utf-8"):
                fehler.append("Zusammenfassung nennt den Siegel-Job nicht")
        finally:
            os.environ.pop("GITHUB_OUTPUT", None)
            os.environ.pop("GITHUB_STEP_SUMMARY", None)
            if alt_out is not None:
                os.environ["GITHUB_OUTPUT"] = alt_out
            if alt_sum is not None:
                os.environ["GITHUB_STEP_SUMMARY"] = alt_sum

        # 5) Leerer Lauf: kein Befund, trotzdem Exit 0 und sauberer Output.
        leer = Path(tmp) / "leer.txt"
        if lesen(leer) != []:
            fehler.append("Fehlende Datei liefert Geister-Befunde")
        if sammeln(leer) != 0:
            fehler.append("sammeln() ohne Befunde endet nicht mit 0")

        # 6) Unlesbare Datei ist kein Absturz (fail-safe, nicht fail-closed:
        #    der Melder ist Beiwerk, nie der Grund für einen roten Lauf).
        kaputt = Path(tmp) / "verzeichnis"
        kaputt.mkdir()
        if lesen(kaputt) != []:
            fehler.append("Verzeichnis statt Datei wird nicht abgefangen")

    if fehler:
        print("🛑 WERKZEUGBEFUND-SELBSTTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print("✅ werkzeugbefund-Selbsttest grün (Melden, Anhängen, Sabotage, "
          "Sammeln, Leerlauf, Fail-safe).")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in args:
        return _selftest()
    if "--sammeln" in args:
        return sammeln()
    if "--liste" in args:
        befunde = lesen()
        for schritt, text in befunde:
            print(f"{schritt}: {text}")
        return 0 if befunde else 1
    if "--melden" in args:
        rest = args[args.index("--melden") + 1:]
        schritt = rest[0] if rest else "unbenannt"
        text = " ".join(rest[1:]) if len(rest) > 1 else "ohne Meldung"
        return melden(schritt, text)
    print(__doc__)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
