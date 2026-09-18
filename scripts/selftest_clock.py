#!/usr/bin/env python3
"""selftest_clock.py – Determinismus-Garantie für Selbsttests (Uhr-Zwang).

WARUM (18.09.2026 – Qualitäts-Gate rot auf main, Run 35312783057, Commit 83526d5)
-------------------------------------------------------------------------------
`scripts/draft_triage.py --selftest` baute seine Prüf-Fixtures mit
„Dateialter = JETZT minus n Tage", verglich das Ergebnis aber gegen ein
EINGEFRORENES Testdatum (`today = datetime.date(2026, 9, 12)`). Am Tag, an dem
der Test geschrieben wurde, war beides dasselbe – der Test war grün. Sechs Tage
später maß dieselbe Zeile 21 statt 27 Tage, ein reifer Entwurf galt nicht mehr
als VERWAIST, und die Wache färbte das Qualitäts-Gate rot, ohne dass jemand den
Code angefasst hätte. Am selben Morgen verbrannte dieselbe Zeile 7½ Minuten im
Content-Reserve-Lauf (Stufe 5, Issue #310).

Ein Selbsttest, der die echte Wanduhr liest, ist kein Test, sondern eine
Verabredung mit dem Kalender: Er funktioniert bis zu einem Datum, das niemand
im Blick hat. Dieselbe Klasse lag noch ein zweites Mal im Repo –
`audio_coverage_check.py` erwartet ein Fixture mit Zukunftsdatum als
„nicht live"; ab dem 24.12.2026 wäre das Qualitäts-Gate jeden Tag rot geworden,
wieder ohne eine einzige Code-Änderung.

Dieses Modul macht die Eigenschaft „läuft an jedem Kalendertag" beweisbar:

  1. `uhr(instant, …)`      Kalender-Uhr ersetzen.
       MODUS_STRIKT      jeder Lesezugriff ist ein Fehler – für Selbsttests,
                         die ihr Testdatum selbst setzen (müssen sie ja).
       MODUS_VERSCHOBEN  die Uhr liefert einen fremden Zeitpunkt – für den
                         Beweis, dass ein Ergebnis nicht vom Datum abhängt.
     `time.time()` bleibt in BEIDEN Modi echt und unangetastet: Dauer- und
     Timeout-Schleifen (`while time.time() - start < 45*60`) dürfen nie
     einfrieren, sonst produziert die Garantie einen Hänger.

  2. `stempel(pfad, tag)`   Dateialter ABSOLUT setzen (lokaler Mittag) statt
     relativ zur echten Uhr. Mittag, weil eine Zeitumstellung dann höchstens
     eine Stunde verschiebt und nie den Kalendertag.

  3. `trap(script, …)`      fremde Uhr um den `--selftest` eines beliebigen
     Skripts legen – die CI-Probe, mit der neue Zeitbomben am Tag ihres
     Entstehens auffallen und nicht an einem Feiertag drei Monate später.

Nutzung:
    python3 scripts/selftest_clock.py --selftest
    python3 scripts/selftest_clock.py --trap scripts/draft_triage.py --offset 1461
    python3 scripts/selftest_clock.py --trap scripts/x.py --offset 97 --selftest-args "--selftest"

Exit: 0 = grün · 1 = Zeitabhängigkeit gefunden (Trap) · 2 = Fehler
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _echt_dt
import os
import runpy
import sys
import time as _echt_time
import types


def _echt(modul):
    """Shim entpacken: immer das ECHTE Modul zurückgeben.

    Ein Selbsttest kann unter einer bereits verschobenen Uhr laufen (die CI-Probe
    legt eine fremde Uhr um einen Selbsttest, der selbst Uhr-Zwang einschaltet).
    Ohne Entpacken würde der zweite Shim auf dem ersten aufsetzen – mit
    Metaklassen-Konflikt statt mit einem Befund.
    """
    return getattr(modul, "FFC_ECHT", modul)


_echt_dt = _echt(_echt_dt)
_echt_time = _echt(_echt_time)

MODUS_STRIKT = "strikt"
MODUS_VERSCHOBEN = "verschoben"
MITTAG = _echt_dt.time(12, 0)


class UhrVerstoss(AssertionError):
    """Ein Selbsttest hat die echte Wanduhr gelesen (Modus `strikt`)."""


# --------------------------------------------------------------------- Shim-Bau
def _metaklasse(basis):
    """`isinstance`/`issubclass` bleiben wahr für die ECHTEN Klassen.

    Ein Shim, der `datetime.date` durch eine Unterklasse ersetzt, würde
    `isinstance(obj, datetime.date)` für Objekte aus PyYAML oder
    `date.fromtimestamp()` still auf False kippen – ein Prüfer würde dann
    Fremddaten für unlesbar halten. Die Metaklasse hält beide Richtungen offen.
    """
    class _Meta(type(basis)):
        def __instancecheck__(cls, obj):
            return isinstance(obj, basis)

        def __subclasscheck__(cls, other):
            return issubclass(other, basis)
    return _Meta


def _shim_datum(instant, modus: str) -> types.ModuleType:
    echt = _echt_dt

    def _lesen(wer: str) -> None:
        if modus == MODUS_STRIKT:
            raise UhrVerstoss(
                f"{wer} liest die echte Wanduhr – ein Selbsttest muss sein "
                "Testdatum selbst setzen (Hilfe: scripts/selftest_clock.py, "
                "`uhr(…, modus=MODUS_STRIKT)` beweist es).")

    class date(echt.date, metaclass=_metaklasse(echt.date)):
        @classmethod
        def today(cls):
            _lesen("datetime.date.today()")
            return instant.date()

    class datetime(echt.datetime, metaclass=_metaklasse(echt.datetime)):
        @classmethod
        def now(cls, tz=None):
            _lesen("datetime.datetime.now()")
            return instant if tz is None else instant.astimezone(tz)

        @classmethod
        def utcnow(cls):
            _lesen("datetime.datetime.utcnow()")
            return instant.astimezone(echt.timezone.utc).replace(tzinfo=None)

        @classmethod
        def today(cls):
            _lesen("datetime.datetime.today()")
            return instant.astimezone().replace(tzinfo=None)

    shim = types.ModuleType("datetime")
    for name in dir(echt):
        if not name.startswith("__"):
            setattr(shim, name, getattr(echt, name))
    shim.date, shim.datetime = date, datetime
    shim.FFC_ECHT = echt
    return shim


def _shim_zeit(instant, modus: str) -> types.ModuleType:
    """Kalender-Zugriffe von `time` ersetzen – `time.time()` bewusst NICHT."""
    echt = _echt_time
    epoche = instant.timestamp()

    def _lesen(wer: str) -> None:
        if modus == MODUS_STRIKT:
            raise UhrVerstoss(
                f"{wer} liest die echte Wanduhr – siehe scripts/selftest_clock.py.")

    def localtime(secs=None):
        if secs is None:
            _lesen("time.localtime()")
            return echt.localtime(epoche)
        return echt.localtime(secs)

    def gmtime(secs=None):
        if secs is None:
            _lesen("time.gmtime()")
            return echt.gmtime(epoche)
        return echt.gmtime(secs)

    def strftime(fmt, tup=None):
        if tup is None:
            _lesen("time.strftime() ohne Zeitwert")
            return echt.strftime(fmt, echt.localtime(epoche))
        return echt.strftime(fmt, tup)

    shim = types.ModuleType("time")
    for name in dir(echt):
        if not name.startswith("__"):
            setattr(shim, name, getattr(echt, name))
    shim.localtime, shim.gmtime, shim.strftime = localtime, gmtime, strftime
    shim.FFC_ECHT = echt
    return shim


@contextlib.contextmanager
def uhr(instant: _echt_dt.datetime | None = None, modus: str = MODUS_VERSCHOBEN,
        module: list | None = None):
    """Kalender-Uhr für den Block ersetzen und danach sauber zurückstellen.

    `module` bindet `datetime`/`time` zusätzlich in den Namensräumen der
    genannten Module neu – nötig, weil ein Modul-Level-`import datetime` sonst
    längst das echte Objekt hält (das ist der ganze Unterschied zwischen
    „sys.modules tauschen" und „wirklich keine echte Uhr mehr lesen").
    """
    if instant is None:
        instant = _echt_dt.datetime.now(_echt_dt.timezone.utc)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=_echt_dt.timezone.utc)
    shim_dt = _shim_datum(instant, modus)
    shim_t = _shim_zeit(instant, modus)
    alt_sys = {"datetime": sys.modules.get("datetime"), "time": sys.modules.get("time")}
    ziele = list(module or [])
    alt_namen = [(m, getattr(m, "datetime", None), getattr(m, "time", None)) for m in ziele]
    try:
        sys.modules["datetime"], sys.modules["time"] = shim_dt, shim_t
        for m in ziele:
            if hasattr(m, "datetime"):
                m.datetime = shim_dt
            if hasattr(m, "time") and getattr(m, "time", None) is _echt_time:
                m.time = shim_t
        yield instant
    finally:
        for key, wert in alt_sys.items():
            if wert is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = wert
        for m, dt, t in alt_namen:
            if dt is not None:
                m.datetime = dt
            if t is not None:
                m.time = t


# ------------------------------------------------------------------ Datei-Alter
def stempel(pfad: str, tag: _echt_dt.date) -> None:
    """mtime ABSOLUT auf `tag` setzen (lokaler Mittag).

    Nie „JETZT minus n Tage": genau das mischt die echte Wanduhr in einen
    Selbsttest mit eingefrorenem Testdatum und macht ihn zum Blindgänger mit
    Verfallsdatum (siehe Modul-Doku). Absolut heißt: derselbe Fixture-Tag ist
    an jedem Kalendertag, in jeder Zeitzone und unter jeder fremden Uhr
    dasselbe Dateialter.
    """
    zeit = _echt_dt.datetime.combine(tag, MITTAG).timestamp()
    os.utime(pfad, (zeit, zeit))


def tag_von(pfad: str) -> _echt_dt.date:
    """Kalendertag, den `stempel` gesetzt hat (Rücklese-Kontrolle)."""
    return _echt_dt.date.fromtimestamp(os.path.getmtime(pfad))


# ------------------------------------------------------------------------ Trap
def trap(script: str, offset_tage: int, args: tuple[str, ...] = ("--selftest",),
         modus: str = MODUS_VERSCHOBEN) -> int:
    """`--selftest` eines Skripts unter fremder Uhr ausführen; Exit-Code zurück.

    Die Uhr wird NACH VORN gestellt (offset > 0), weil die Zeit im Betrieb nur
    in diese Richtung läuft: Eine Wache, die heute grün ist, muss es auch in
    97 Tagen und in vier Jahren noch sein. Ein Zurückdrehen prüft dagegen
    Fälle, die real nie eintreten, und erzeugt Fehlalarme.
    """
    instant = (_echt_dt.datetime.now(_echt_dt.timezone.utc)
               + _echt_dt.timedelta(days=offset_tage, hours=3, minutes=7))
    pfad = os.path.abspath(script)
    if not os.path.isfile(pfad):
        raise FileNotFoundError(pfad)
    # `python3 scripts/x.py` legt scripts/ auf sys.path[0]; runpy tut das nicht.
    # Ohne diese Zeile scheitern Wachen an ihren eigenen Hilfsmodulen
    # (post_utils, groq_config, …) – ein Fehlalarm der Probe, kein Befund.
    verzeichnis = os.path.dirname(pfad)
    if verzeichnis not in sys.path:
        sys.path.insert(0, verzeichnis)
    sys.argv = [pfad, *args]
    with uhr(instant, modus):
        try:
            runpy.run_path(pfad, run_name="__main__")
        except SystemExit as exc:
            code = exc.code
            return 0 if code is None else (code if isinstance(code, int) else 1)
        except UhrVerstoss as exc:
            print(f"🛑 Uhr-Verstoß: {exc}")
            return 2
    return 0


# ------------------------------------------------------------------- Selbsttest
def _selftest() -> int:
    import shutil
    import tempfile
    fehler: list[str] = []
    probe = _echt_dt.datetime(2031, 5, 4, 3, 2, 1, tzinfo=_echt_dt.timezone.utc)
    tmp = tempfile.mkdtemp(prefix="selftest-clock-")
    try:
        # 1) strikt: jeder Lesezugriff auf die echte Uhr muss fliegen.
        #    `datetime`/`time` werden IM Block neu importiert – nur so landet der
        #    Shim im Namensraum. Die Modul-Aliase `_echt_dt`/`_echt_time` bleiben
        #    absichtlich echt: sie sind die Vergleichsgrundlage dieses Tests.
        with uhr(probe, MODUS_STRIKT):
            import datetime as dt
            import time as tm
            for name, fn in (("date.today()", dt.date.today),
                             ("datetime.now()", dt.datetime.now),
                             ("datetime.utcnow()", dt.datetime.utcnow),
                             ("datetime.today()", dt.datetime.today),
                             ("time.localtime()", tm.localtime),
                             ("time.gmtime()", tm.gmtime),
                             ("time.strftime()", lambda: tm.strftime("%Y-%m-%d"))):
                try:
                    fn()
                    fehler.append(f"strikt: {name} liest weiter die echte Uhr")
                except UhrVerstoss:
                    pass
            # time.time() MUSS echt bleiben und weiterlaufen: Eine Dauer-Schleife
            # (`while time.time() - start < 45*60`) unter einer eingefrorenen Uhr
            # wäre ein Hänger – die Garantie darf keinen produzieren.
            t1 = tm.time()
            tm.sleep(0.01)
            if not tm.time() > t1:
                fehler.append("time.time() steht still – Dauer-Schleifen würden hängen")
            # Umrechnungen mit explizitem Zeitwert bleiben erlaubt und echt
            if dt.datetime.fromtimestamp(1_600_000_000, dt.timezone.utc).year != 2020:
                fehler.append("strikt blockiert fromtimestamp(epoch) – Umrechnung muss frei bleiben")

        # 2) verschoben: Kalender ist fremd, Umrechnungen bleiben echt
        with uhr(probe, MODUS_VERSCHOBEN):
            import datetime as dt
            import time as tm
            if dt.date.today() != probe.date():
                fehler.append("verschoben: date.today() liefert nicht den Fremdwert")
            if dt.datetime.now(dt.timezone.utc).date() != probe.date():
                fehler.append("verschoben: datetime.now(tz) liefert nicht den Fremdwert")
            if dt.datetime.utcnow().year != 2031:
                fehler.append("verschoben: datetime.utcnow() liefert nicht den Fremdwert")
            if tm.localtime().tm_year != 2031 or tm.gmtime().tm_year != 2031:
                fehler.append("verschoben: time.localtime()/gmtime() ignorieren die fremde Uhr")
            if tm.strftime("%Y") != "2031":
                fehler.append("verschoben: time.strftime() ohne Zeitwert ignoriert die fremde Uhr")
            fest = 1_600_000_000
            if tm.localtime(fest).tm_year != 2020:
                fehler.append("time.localtime(epoch) wird verstellt – Umrechnung muss echt bleiben")
            if dt.datetime.fromtimestamp(fest, dt.timezone.utc).year != 2020:
                fehler.append("datetime.fromtimestamp wird verstellt – Umrechnung muss echt bleiben")
            if dt.date.fromisoformat("2026-09-12") != _echt_dt.date(2026, 9, 12):
                fehler.append("fromisoformat wird verstellt")

        # 3) isinstance bleibt in beide Richtungen wahr (PyYAML-/C-API-Objekte)
        with uhr(probe, MODUS_VERSCHOBEN):
            import datetime as dt
            if not isinstance(_echt_dt.date(2026, 9, 12), dt.date):
                fehler.append("isinstance(echtes date, Shim-date) kippt – Fremddaten würden unlesbar")
            if not isinstance(_echt_dt.datetime(2026, 9, 12), dt.datetime):
                fehler.append("isinstance(echtes datetime, Shim-datetime) kippt")
            if not isinstance(dt.date.today(), _echt_dt.date):
                fehler.append("Shim-date ist kein echtes date – Folge-Code würde ablehnen")
            if not isinstance(_echt_dt.date.fromtimestamp(1_600_000_000), dt.date):
                fehler.append("Objekte aus der C-API fallen durch die Shim-Prüfung")

        # 3b) `module=…` bindet den Shim in einen fremden Namensraum und stellt zurück
        dummy = types.ModuleType("dummy_wache")
        dummy.datetime, dummy.time = _echt_dt, _echt_time
        with uhr(probe, MODUS_STRIKT, module=[dummy]):
            try:
                dummy.datetime.date.today()
                fehler.append("module=…: fremder Namensraum liest weiter die echte Uhr")
            except UhrVerstoss:
                pass
            if dummy.time is _echt_time:
                fehler.append("module=…: `time` wurde im fremden Namensraum nicht neu gebunden")
        if dummy.datetime is not _echt_dt or dummy.time is not _echt_time:
            fehler.append("module=…: fremder Namensraum wurde nicht zurückgestellt")

        # 3c) Verschachtelung: Die CI-Probe legt eine fremde Uhr um einen
        #     Selbsttest, der selbst Uhr-Zwang einschaltet (draft_triage tut das).
        #     Der innere Wert muss gelten und der äußere danach wieder da sein.
        innen = _echt_dt.datetime(2026, 9, 12, 12, 0, tzinfo=_echt_dt.timezone.utc)
        with uhr(probe, MODUS_VERSCHOBEN):
            import datetime as dt
            with uhr(innen, MODUS_STRIKT):
                import datetime as dt2
                try:
                    dt2.date.today()
                    fehler.append("verschachtelt: innere Uhr ist nicht strikt")
                except UhrVerstoss:
                    pass
            if dt.date.today() != probe.date():
                fehler.append("verschachtelt: äußere Uhr wurde nicht zurückgestellt")
            if not isinstance(dt.date.today(), _echt_dt.date):
                fehler.append("verschachtelt: Shim-Kette verliert die isinstance-Treue")

        # 4) stempel: absolut, zeitzonenfest, rücklesbar
        pfad = os.path.join(tmp, "fixture.md")
        open(pfad, "w", encoding="utf-8").write("x")
        for tag in (_echt_dt.date(2026, 9, 12), _echt_dt.date(2026, 3, 29),   # DST-Anfang
                    _echt_dt.date(2026, 10, 25), _echt_dt.date(2028, 2, 29),   # DST-Ende/Schalttag
                    _echt_dt.date(1999, 12, 31)):
            stempel(pfad, tag)
            if tag_von(pfad) != tag:
                fehler.append(f"stempel({tag}) liest sich als {tag_von(pfad)} zurück")
        # Beweis der Zeitzonen-Unabhängigkeit, wo die Plattform mitspielt
        if hasattr(_echt_time, "tzset"):
            alt = os.environ.get("TZ")
            try:
                for zone in ("Europe/Berlin", "UTC", "Pacific/Kiritimati", "Pacific/Niue",
                             "America/New_York"):
                    os.environ["TZ"] = zone
                    _echt_time.tzset()
                    stempel(pfad, _echt_dt.date(2026, 10, 25))
                    if tag_von(pfad) != _echt_dt.date(2026, 10, 25):
                        fehler.append(f"stempel ist in TZ={zone} nicht tagtreu ({tag_von(pfad)})")
            finally:
                if alt is None:
                    os.environ.pop("TZ", None)
                else:
                    os.environ["TZ"] = alt
                _echt_time.tzset()

        # 5) trap: findet eine datumsabhängige Wache, lässt eine feste grün.
        #    Die Bombe erwartet ein Datum, das aus der ECHTEN Uhr abgeleitet wird
        #    (heute + 2 Tage) – sonst wäre dieser Selbsttest selbst eine
        #    Zeitbombe. Unter der echten Uhr ist sie grün, unter einer um 1461
        #    Tage vorgestellten Uhr rot: genau die Signatur des draft_triage-Falls.
        os.environ["BOMB_GRENZE"] = (_echt_dt.date.today()
                                     + _echt_dt.timedelta(days=2)).isoformat()
        bomb = os.path.join(tmp, "bombe.py")
        open(bomb, "w", encoding="utf-8").write(
            "import datetime, os, sys\n"
            "grenze = datetime.date.fromisoformat(os.environ['BOMB_GRENZE'])\n"
            "sys.exit(0 if grenze > datetime.date.today() else 1)\n")
        fest_script = os.path.join(tmp, "fest.py")
        open(fest_script, "w", encoding="utf-8").write(
            "import datetime, sys\n"
            "ref = datetime.date(2026, 9, 12)\n"
            "sys.exit(0 if (ref - datetime.date(2026, 8, 16)).days == 27 else 1)\n")
        if trap(bomb, 0) != 0:
            fehler.append("Bombe ist schon ohne Uhr-Verschiebung rot – Prüf-Aufbau kaputt")
        if trap(bomb, 1461) == 0:
            fehler.append("trap lässt eine datumsabhängige Wache grün durch")
        if trap(bomb, 97) == 0:
            fehler.append("trap lässt eine datumsabhängige Wache bei kleinem Offset durch")
        if trap(fest_script, 1461) != 0:
            fehler.append("trap meldet eine datumsunabhängige Wache fälschlich")
        if trap(fest_script, 0) != 0:
            fehler.append("trap verfälscht das Ergebnis bei Offset 0")
        try:
            trap(os.path.join(tmp, "gibt-es-nicht.py"), 1)
            fehler.append("trap schweigt zu einem fehlenden Skript")
        except FileNotFoundError:
            pass
    except Exception as exc:  # noqa: BLE001
        fehler.append(f"Ausführung: {exc.__class__.__name__}: {exc}")
    finally:
        os.environ.pop("BOMB_GRENZE", None)
        shutil.rmtree(tmp, ignore_errors=True)
    if fehler:
        print("🛑 selftest_clock-Selbsttest FEHLGESCHLAGEN:")
        for f in fehler:
            print("  -", f)
        return 2
    print("✅ Uhr-Zwang-Selbsttest grün: strikt/verschoben, isinstance-Treue, "
          "absolutes Dateialter (5 Tage + 5 Zeitzonen), Trap findet Zeitbomben.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Determinismus-Garantie für Selbsttests")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--trap", metavar="SCRIPT", help="Selbsttest eines Skripts unter fremder Uhr")
    ap.add_argument("--offset", type=int, default=1461, help="Tage in die Zukunft (Standard 1461)")
    ap.add_argument("--selftest-args", default="--selftest")
    ap.add_argument("--strikt", action="store_true",
                    help="Trap-Modus: jede echte Uhr-Zeitlesung ist ein Fehler")
    args = ap.parse_args()
    if args.trap:
        code = trap(args.trap, args.offset, tuple(args.selftest_args.split()),
                    MODUS_STRIKT if args.strikt else MODUS_VERSCHOBEN)
        if code:
            print(f"🛑 {args.trap} --selftest ist datumsabhängig "
                  f"(Uhr um {args.offset} Tage vorgestellt, Exit {code}).")
            return 1
        print(f"✅ {args.trap}: Selbsttest bleibt unter einer um {args.offset} "
              "Tage vorgestellten Uhr grün.")
        return 0
    return _selftest() if args.selftest else 2


if __name__ == "__main__":
    sys.exit(main())
