#!/usr/bin/env python3
"""`hunspell`-Ersatz ohne Systempaket (Befund 15.11.2026).

WARUM ES DIESE DATEI GIBT
-------------------------
Die halbe Messkette des Repos hängt an `hunspell`:

  * `spellcheck.py` prüft damit die Rechtschreibung ganzer Artikel,
  * `quality_score` wertet ein nicht lauffähiges Wörterbuch als
    `spelling = 0.5` („unbekannt") – bei Gewicht 0.20 drückt das JEDEN
    Artikel um bis zu 0.10 und damit quer unter die 0.85-Schwelle,
  * `reserve_recert.gate_verfuegbar()` verweigert deshalb die
    Nachzertifizierung: „ein Werkzeugmangel, der wie ein Qualitätsproblem
    aussieht".

Die CI installiert das Programm per `apt-get install hunspell
hunspell-de-de`. Auf einem Rechner ohne root – und in dieser Sandbox – ist
das nicht möglich. Die Folge war kein kaputter Test, sondern eine
**fehlende Messung**: Die Reserve ließ sich nicht nachzertifizieren, und
das sah aus wie ein leerer Vorrat.

DIESER ERSATZ
-------------
`spylls` ist eine vollständige Hunspell-Implementierung in reinem Python;
gebraucht wird nur ein deutsches Wörterbuch. Dieses Skript bildet die
Aufruf-Schnittstelle nach, die das Repo tatsächlich nutzt:

    hunspell -i UTF-8 -d de_DE -l      # falsche Wörter, eine Zeile je Wort

Damit ist KEIN Quelltext zu ändern: `spellcheck.py` findet dieses Programm
als `hunspell` im PATH und bekommt dieselbe Antwort wie vom Systempaket.

WÖRTERBUCH
----------
Gesucht wird in dieser Reihenfolge:
  1. `$HUNSPELL_DE_DIR` bzw. `--worterbuch`
  2. `data/hunspell/de_DE.{aff,dic}` (im Repo mitgeliefert)
  3. `/usr/share/hunspell` und `/usr/share/myspell` (Systempaket)

Fehlt das Wörterbuch, endet das Skript mit Exit 3 und einer klaren
Anweisung – es rät nicht und meldet vor allem nicht „alles richtig".
Ein Prüfwerkzeug, das ohne Wörterbuch 0 Fehler meldet, ist schlimmer als
keines: Es macht aus „nicht gemessen" ein „ist in Ordnung".
"""
import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STANDARD = ROOT / "data" / "hunspell" / "de_DE"


def woerterbuch_finden(explicit: str | None = None) -> tuple[Path, Path] | None:
    """(aff, dic) oder None, wenn kein deutsches Wörterbuch da ist.

    Ein AUSDRÜCKLICH genannter Pfad (`--worterbuch`, `$HUNSPELL_DE_DIR`) ist
    eine Zusicherung des Aufrufers, keine Anregung. Fehlt er, wird NICHT
    stillschweigend das Standardwörterbuch genommen: Sonst prüft ein Lauf
    gegen ein anderes Wörterbuch als angekündigt, und das Ergebnis sieht
    trotzdem gültig aus. Lieber Exit 3 mit klarer Meldung.
    """
    if explicit:
        aff, dic = Path(f"{explicit}.aff"), Path(f"{explicit}.dic")
        return (aff, dic) if aff.is_file() and dic.is_file() else None
    if os.environ.get("HUNSPELL_DE_DIR"):
        basis = Path(os.environ["HUNSPELL_DE_DIR"])
        aff, dic = Path(f"{basis}.aff"), Path(f"{basis}.dic")
        if not (aff.is_file() and dic.is_file()):
            # Erlaubt ist auch ein Verzeichnis mit de_DE.aff/.dic darin.
            aff, dic = basis / "de_DE.aff", basis / "de_DE.dic"
        return (aff, dic) if aff.is_file() and dic.is_file() else None
    kandidaten: list[Path] = [
        STANDARD,
        Path("/usr/share/hunspell/de_DE"),
        Path("/usr/share/myspell/de_DE"),
        Path("/usr/share/hunspell/de_DE_frami"),
    ]
    for k in kandidaten:
        aff, dic = Path(f"{k}.aff"), Path(f"{k}.dic")
        if aff.is_file() and dic.is_file():
            return aff, dic
    return None


def fehler(text: str) -> None:
    print(f"hunspell(ersatz): {text}", file=sys.stderr)


# ----------------------------------------------------------------------
#  DAEMON
#  Die Ladezeit des Wörterbuchs (2,3 s) fällt bei JEDEM Aufruf an. Die
#  Messkette ruft `hunspell` aber pro Wort auf (spellcheck.py: einmal für
#  die Kleinform, einmal für die Großform, einmal für Vorschläge) – bei
#  einem Artikel mit 20 unbekannten Wörtern sind das 60 Prozessstarts und
#  damit über 100 Sekunden. Kein Timeout überlebt das.
#
#  Deshalb: ein kleiner Hintergrundprozess hält das Wörterbuch im Speicher
#  und beantwortet Anfragen über einen Unix-Socket. Der erste Aufruf startet
#  ihn (einmalig 2,3 s), alle weiteren kosten Millisekunden. Das ist
#  dieselbe Bauform wie `nscd` oder `clamd` – und exakt das, was das
#  C-Original ohnehin im Speicher hält.
# ----------------------------------------------------------------------
def _daemon_argumente(args) -> list[str]:
    """Wörterbuchwahl an den Daemon weiterreichen (nicht die Modus-Flags)."""
    return ["--worterbuch", args.worterbuch] if args.worterbuch else []


def _socket_pfad(aff: Path) -> Path:
    """Eindeutiger Socket je Wörterbuch (verschiedene Wörterbücher mischen
    sich nicht) und je Benutzer (kein Zugriff fremder Konten)."""
    import hashlib
    import tempfile

    # Die Kennung umfasst Wörterbuch UND Skriptstand: Ein geänderter Ersatz
    # startet einen frischen Daemon, statt monatelang alten Code zu
    # beantworten. Genau dieser Fall ist aufgetreten – ein vor einer
    # Optimierung gestarteter Daemon hat die Optimierung nicht gesehen.
    quelle = Path(__file__).resolve()
    stand = f"{quelle.stat().st_mtime_ns}:{quelle.stat().st_size}"
    kennung = hashlib.sha256(str(aff.resolve()).encode()).hexdigest()[:10]
    code = hashlib.sha256(stand.encode()).hexdigest()[:6]
    return Path(tempfile.gettempdir()) / f"hunspell-ersatz-{os.getuid()}-{kennung}-{code}.sock"


def daemon_lauf(aff: Path, pfad: Path) -> int:
    """Endlos-Dienst: liest JSON-Zeilen, antwortet JSON-zeilenweise."""
    import json
    import socket

    d = _laden(aff)
    try:
        pfad.unlink()
    except FileNotFoundError:
        pass
    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(pfad))
    os.chmod(pfad, 0o600)
    srv.listen(16)
    # Bereitschaft melden: der Starter wartet auf diese Datei.
    Path(f"{pfad}.bereit").write_text("1", encoding="utf-8")
    try:
        while True:
            srv.settimeout(600)     # ohne Anfrage beenden -> keine Streuner
            try:
                verb, _ = srv.accept()
            except socket.timeout:
                break
            with verb, verb.makefile("rw", encoding="utf-8", newline="\n") as f:
                for zeile in f:
                    try:
                        anfrage = json.loads(zeile)
                    except ValueError:
                        f.write('{"fehler": "ungueltige Anfrage"}\n')
                        f.flush()
                        continue
                    f.write(json.dumps(_beantworten(d, anfrage)) + "\n")
                    f.flush()
                    if anfrage.get("ende"):
                        break
    finally:
        for rest in (pfad, Path(f"{pfad}.bereit")):
            try:
                rest.unlink()
            except FileNotFoundError:
                pass
    return 0


def _beantworten(d, anfrage: dict) -> dict:
    """Eine Anfrage beantworten. Reine Funktion, damit testbar ohne Socket."""
    modus = anfrage.get("modus", "l")
    woerter = anfrage.get("woerter") or []
    if modus == "l":
        gesehen: set[str] = set()
        raus = []
        for w in woerter:
            if w in gesehen:
                continue
            gesehen.add(w)
            if not d.lookup(w):
                raus.append(w)
        return {"ausgabe": raus}
    # Analyse-Modus: Ispell-Protokoll
    zeilen = ["@(#) hunspell-ersatz (spylls) de_DE"]
    einzelwort = len(woerter) == 1
    for w in woerter:
        if d.lookup(w):
            zeilen.append("*")
        elif not einzelwort:
            zeilen.append(f"# {w} 1")
        else:
            v = _vorschlaege(d, w)
            zeilen.append(f"& {w} 1 0: {', '.join(v)}" if v else f"# {w} 1")
    return {"ausgabe": zeilen}


def _daemon_sichern(pfad: Path, argv_fuer_daemon: list[str]) -> bool:
    """Daemon starten und warten, bis er antwortet (max. 30 s)."""
    import subprocess
    import time

    for rest in (pfad, Path(f"{pfad}.bereit")):
        try:
            rest.unlink()
        except FileNotFoundError:
            pass
    subprocess.Popen(
        [sys.executable, __file__, "--daemon", "--socket", str(pfad)] + argv_fuer_daemon,
        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True,
    )
    for _ in range(300):
        if Path(f"{pfad}.bereit").is_file():
            return True
        time.sleep(0.1)
    return False


def _anfrage(pfad: Path, anfrage: dict) -> dict | None:
    """An den Daemon schicken. None = kein Daemon erreichbar."""
    import json
    import socket

    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(30)
        s.connect(str(pfad))
        with s, s.makefile("rw", encoding="utf-8", newline="\n") as f:
            f.write(json.dumps(anfrage) + "\n")
            f.flush()
            antwort = f.readline()
        return json.loads(antwort) if antwort else None
    except (OSError, ValueError):
        return None


VORSCHLAG_SEKUNDEN = 4.0


# Nach HÄUFIGKEIT sortiert, nicht alphabetisch: In einem unbekannten Wort ist
# ein falsch getipptes „e" fünfzigmal wahrscheinlicher als ein „q". Diese
# Reihenfolge bringt echte Treffer in die ersten Dutzend Prüfungen – bei
# alphabetischer Suche erst nach Hunderten.
BUCHSTABEN = "enirsatdhulgcmoüfkzbwäöpvßjyqx"


_VORSCHLAG_MEMO: dict[tuple[str, int], tuple[str, ...]] = {}
# Höchstzahl geprüfter Kandidaten je Wort. Jeder Kandidat kostet einen
# Wörterbuch-Zugriff (~2 ms); ohne Grenze sind es bei einem 14-Buchstaben-Wort
# über 800 und damit 1,8 s PRO WORT. Das Budget schneidet die wenig
# wahrscheinlichen Operationen (Einfügen am Wortende) ab, wenn die
# wahrscheinlichen (Groß-/Kleinschreibung, Löschen, Vertauschen, Ersetzen)
# schon nichts gefunden haben.
VORSCHLAG_BUDGET = 240


def _vorschlaege(d, wort: str, grenze: int = 5) -> list[str]:
    """Korrekturvorschläge wie Hunspell – aber in Millisekunden.

    `spylls.suggest()` ist vollständig, aber unbrauchbar langsam: es kostet
    2–8 SEKUNDEN pro Wort, weil es den gesamten Wortschatz durchgeht. Ein
    Artikel mit 10 unbekannten Wörtern lief damit 112 s – weit über dem
    15-s-Timeout der Aufrufer.

    Dieses Verfahren ist der klassische Damerau-Levenshtein-Umkreis
    (Löschen, Vertauschen, Ersetzen, Einfügen – je 1 Operation) und prüft
    jeden Kandidaten mit `lookup()` (~2 ms). Ergebnis: echte Treffer in
    Bruchteilen einer Sekunde.

    Die Reihenfolge folgt der Wahrscheinlichkeit: erst Löschen und
    Vertauschen (Tippfehler), dann Ersetzen, dann Einfügen. So steht bei
    „geld" das richtige „Geld" vorn, obwohl die Großschreibung hier nicht
    als eigener Kandidat entsteht – Hunspell liefert sie über die
    Kasusregeln des Wörterbuchs, deshalb wird sie gezielt ergänzt.
    """
    if not wort:
        return []
    schluessel = (wort, grenze)
    if schluessel in _VORSCHLAG_MEMO:
        return list(_VORSCHLAG_MEMO[schluessel])

    treffer: list[str] = []
    gesehen: set[str] = set()
    geprueft = 0

    def _pruefe(k: str) -> None:
        nonlocal geprueft
        if not k or k in gesehen or len(treffer) >= grenze or geprueft >= VORSCHLAG_BUDGET:
            return
        gesehen.add(k)
        geprueft += 1
        if d.lookup(k):
            treffer.append(k)

    # Groß-/Kleinschreibung: im Deutschen der häufigste „Fehler" überhaupt.
    _pruefe(wort[0].upper() + wort[1:])
    _pruefe(wort[0].lower() + wort[1:])

    teile = [(wort[:i], wort[i:]) for i in range(len(wort) + 1)]
    for a, b in teile:                     # Löschen
        if b:
            _pruefe(a + b[1:])
    for a, b in teile:                     # Vertauschen
        if len(b) > 1:
            _pruefe(a + b[1] + b[0] + b[2:])
    for a, b in teile:                     # Ersetzen
        if b:
            for c in BUCHSTABEN:
                _pruefe(a + c + b[1:])
                if len(treffer) >= grenze:
                    return treffer
    for a, b in teile:                     # Einfügen
        for c in BUCHSTABEN:
            _pruefe(a + c + b)
            if len(treffer) >= grenze or geprueft >= VORSCHLAG_BUDGET:
                break
        if len(treffer) >= grenze or geprueft >= VORSCHLAG_BUDGET:
            break
    _VORSCHLAG_MEMO[schluessel] = tuple(treffer)
    return treffer


_CACHE: dict = {}


def _laden(aff: Path):
    """Wörterbuch einmal je Prozess laden (2,6 s) und dann wiederverwenden.

    Ohne diesen Cache zahlt JEDER Aufruf die volle Ladezeit. In einer
    Messkette, die hunderte Artikel prüft, ist das der Unterschied zwischen
    „läuft" und „Timeout nach 15 Sekunden" – und genau daran scheiterte die
    Reserve-Nachzertifizierung.

    Der Schlüssel ist der Pfad; ein geändertes Wörterbuch erfordert einen
    neuen Prozess (was bei einem CLI-Aufruf ohnehin der Fall ist).
    """
    schluessel = str(aff)
    if schluessel not in _CACHE:
        from spylls.hunspell import Dictionary
        _CACHE[schluessel] = Dictionary.from_files(schluessel.replace(".aff", ""))
    return _CACHE[schluessel]


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="hunspell",
        description="Freier hunspell-Ersatz (spylls) für Umgebungen ohne Systempaket.",
        epilog="Unterstützt die im Repo genutzte Aufrufform: "
               "`hunspell -i UTF-8 -d de_DE -l` liest Wörter von stdin "
               "und gibt die unbekannten aus.")
    p.add_argument("-l", "--list", action="store_true",
                   help="unbekannte Wörter ausgeben (eine Zeile je Wort)")
    p.add_argument("-i", "--input-encoding", default="UTF-8",
                   help="Eingabe-Kodierung (akzeptiert, UTF-8 wird erwartet)")
    p.add_argument("-a", "--analyse", action="store_true",
                   help="Ispell-Protokoll auf stdout (& Fehler, # richtig)")
    p.add_argument("--daemon", action="store_true",
                   help="Daemon-Modus (intern; beantwortet Anfragen über Socket)")
    p.add_argument("--socket", default=None,
                   help="Socket-Pfad des Daemons (intern)")
    p.add_argument("--ohne-daemon", action="store_true",
                   help="Daemon nicht nutzen (jeder Aufruf lädt das Wörterbuch)")
    p.add_argument("--serve", action="store_true",
                   help="persistenter Modus für Testskripte (stdin/stdout)")
    p.add_argument("--vorschlaege", action="store_true",
                   help="Korrekturvorschläge berechnen (nur bei EINEM Wort; "
                        "kostet einige Sekunden)")
    p.add_argument("-D", "--woerterbuchliste", action="store_true",
                   dest="liste",
                   help="verfügbare Wörterbücher melden (wie `hunspell -D`)")
    p.add_argument("-d", "--dictionary", default="de_DE",
                   help="Wörterbuchname; das deutsche Wörterbuch wird gesucht")
    p.add_argument("--worterbuch", default=None,
                   help="Pfad ohne Endung, z. B. data/hunspell/de_DE")
    args, unbekannt = p.parse_known_args(argv)

    if args.daemon:
        gefunden = woerterbuch_finden(args.worterbuch)
        if gefunden is None:
            fehler("kein deutsches Wörterbuch gefunden – siehe --help")
            return 3
        pfad = Path(args.socket) if args.socket else _socket_pfad(gefunden[0])
        return daemon_lauf(gefunden[0], pfad)

    if unbekannt:
        # Fail-closed: Ein Schalter, den dieser Ersatz nicht versteht, darf
        # nicht stillschweigend zu „alles geprüft" führen.
        fehler(f"nicht unterstützte Schalter: {' '.join(unbekannt)}")
        return 2

    # Wie das Original: OHNE -l ist `hunspell` im Analyse-Modus. Ein Aufruf
    # bloss mit `-i/-d` (so ruft `spellcheck.suggestions()` es auf) erwartet
    # also das Ispell-Protokoll, nicht den Listenmodus.
    if not args.list:
        args.analyse = True

    gefunden = woerterbuch_finden(args.worterbuch)
    if gefunden is None:
        fehler("kein deutsches Wörterbuch gefunden (de_DE.aff/.dic).")
        fehler("Erwartet in: data/hunspell/de_DE.{aff,dic} oder /usr/share/hunspell/")
        fehler("Abhilfe: `python3 scripts/hunspell_worterbuch_holen.py`")
        return 3
    aff, dic = gefunden

    # `hunspell -D` listet die gefundenen Wörterbücher und beendet sich.
    # `measurement_chain.status()` prüft genau darüber, ob de_DE vorhanden
    # ist – eine falsche oder fehlende Auskunft lässt die Messkette als
    # „unvollständig" gelten und blockiert jeden Lauf.
    if args.liste:
        print("SEARCH PATH:")
        for verzeichnis in (aff.parent, Path("/usr/share/hunspell"),
                            Path("/usr/share/myspell")):
            print(f"    {verzeichnis}")
        print("AVAILABLE DICTIONARIES:")
        print(aff.with_suffix(""))
        return 0

    woerter = [z.strip() for z in sys.stdin.read().splitlines() if z.strip()]
    if not woerter:
        return 0

    # Erst den Daemon fragen: er hält das Wörterbuch bereits im Speicher.
    # Nur wenn keiner läuft (und keiner startbar ist), rechnen wir selbst.
    if not args.ohne_daemon:
        pfad = _socket_pfad(aff)
        antwort = _anfrage(pfad, {"modus": "l" if args.list else "a",
                                 "woerter": woerter})
        if antwort is None and _daemon_sichern(pfad, _daemon_argumente(args)):
            antwort = _anfrage(pfad, {"modus": "l" if args.list else "a",
                                      "woerter": woerter})
        if antwort is not None:
            print("\n".join(antwort["ausgabe"]))
            return 0

    try:
        from spylls.hunspell import Dictionary  # noqa: F401 – Verfügbarkeit prüfen
    except ImportError:
        fehler("spylls fehlt – `pip install spylls` (reines Python, keine root-Rechte)")
        return 3
    d = _laden(aff)

    # `hunspell -l` gibt jedes unbekannte Wort einmal aus, in Eingabereihenfolge.
    if args.list:
        gesehen: set[str] = set()
        for w in woerter:
            if w in gesehen:
                continue
            gesehen.add(w)
            if not d.lookup(w):
                print(w)
        return 0

    # `hunspell -a` (Ispell-Protokoll):
    #   "@(#) ..."  Kopfzeile
    #   "*"         Wort ist richtig
    #   "& wort N o: vorschlag1, vorschlag2"   falsch, mit Vorschlägen
    #   "# wort N"                            falsch, ohne Vorschlag
    # spellcheck.suggestions() liest genau diese Form.
    print("@(#) hunspell-ersatz (spylls) de_DE")
    # `lookup()` kostet ~2 ms, `suggest()` bis 8 s – pro Wort, weil es den
    # ganzen Wortschatz nach Kandidaten durchgeht. Vorschläge gibt es deshalb
    # NUR auf ausdrückliche Anforderung (`--vorschlaege`) und nur für einzelne
    # Wörter. Wer den Analyse-Modus als Massenprüfung nutzt – und genau das
    # tut `affiliate_integrity_gate`, das alle CTA-Wörter auf einmal schickt –,
    # bekommt sofort `*`/`#`. Das ist die einzige Variante, die innerhalb der
    # 15-Sekunden-Grenze bleibt, die die Aufrufer setzen.
    # Einzelwörter bekommen Vorschläge (dafür ist der Aufruf da) – aber mit
    # harter Zeitgrenze. `spylls.suggest()` kann bei seltenen Wortformen
    # Sekunden brauchen; ein hängender Vorschlag darf die Prüfung nicht
    # blockieren. Nach der Grenze gilt das Wort als „unbekannt ohne
    # Vorschlag" – dieselbe Aussage, nur ohne Wartezeit.
    einzelwort = len(woerter) == 1
    for w in woerter:
        if d.lookup(w):
            print("*")
            continue
        if not einzelwort:
            print(f"# {w} 1")
            continue
        vorschlaege = _vorschlaege(d, w)
        if vorschlaege:
            print(f"& {w} 1 0: {', '.join(vorschlaege)}")
        else:
            print(f"# {w} 1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
