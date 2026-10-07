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
    python3 scripts/selftest_clock.py --trap-modul scripts.tests.test_x --offset 97
    python3 scripts/selftest_clock.py --trap-discover scripts/tests --offset 97

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


def _ist_uhrbindung(wert) -> bool:
    """Zeigt `wert` auf das echte `datetime`/`time`-Modul – oder auf einen Shim?

    Der zweite Fall ist der wichtige: Läuft bereits eine fremde Uhr und wird ein
    Modul erst DANACH importiert, dann hält es nicht das echte Modul, sondern
    den Shim der äußeren Uhr.
    """
    if wert is _echt_dt or wert is _echt_time:
        return True
    return getattr(wert, "FFC_ECHT", None) in (_echt_dt, _echt_time)


def _umbiegen_namen(m) -> dict:
    """Namen im Namensraum von `m`, die auf eine Uhr zeigen (auch als Alias).

    Ohne das bliebe `import datetime as dt` unentdeckt: Der Modulname ist `dt`,
    nicht `datetime`. Am 07.10.2026 scheiterte genau daran der Uhr-Pin in
    `test_pflichtcheck` – die Wache las weiter die fremde Uhr, obwohl der Test
    sie festgeschrieben hatte.
    """
    return {name: wert for name, wert in list(vars(m).items())
            if _ist_uhrbindung(wert)}


def _binde(m, shim_dt, shim_t) -> None:
    """Alle echten Uhr-Referenzen des Namensraums durch die Shims ersetzen."""
    for name, wert in _umbiegen_namen(m).items():
        echt = getattr(wert, "FFC_ECHT", wert)
        setattr(m, name, shim_dt if echt is _echt_dt else shim_t)


@contextlib.contextmanager
def uhr(instant: _echt_dt.datetime | None = None, modus: str = MODUS_VERSCHOBEN,
        module: list | None = None):
    """Kalender-Uhr für den Block ersetzen und danach sauber zurückstellen.

    `module` bindet `datetime`/`time` zusätzlich in den Namensräumen der
    genannten Module neu – nötig, weil ein Modul-Level-`import datetime` sonst
    längst das echte Objekt hält (das ist der ganze Unterschied zwischen
    „sys.modules tauschen" und „wirklich keine echte Uhr mehr lesen").

    Während der fremden Uhr steht `FFC_FREMD_UHR` (ISO-Zeitpunkt) in der
    Umgebung. Das ist der ehrliche Ausweg für Tests, die den ECHTEN Bestand am
    ECHTEN Kalendertag prüfen: Sie melden sich damit ausdrücklich ab
    (`skipIf`), statt unter einer vorgestellten Uhr etwas zu behaupten, was sie
    nicht geprüft haben – und statt einen Fehlalarm zu erzeugen.
    """
    if instant is None:
        instant = _echt_dt.datetime.now(_echt_dt.timezone.utc)
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=_echt_dt.timezone.utc)
    shim_dt = _shim_datum(instant, modus)
    shim_t = _shim_zeit(instant, modus)
    alt_sys = {"datetime": sys.modules.get("datetime"), "time": sys.modules.get("time")}
    ziele = list(module or [])
    alt_namen = [(m, dict(_umbiegen_namen(m))) for m in ziele]
    alt_fremd = os.environ.get("FFC_FREMD_UHR")
    try:
        os.environ["FFC_FREMD_UHR"] = instant.isoformat()
        sys.modules["datetime"], sys.modules["time"] = shim_dt, shim_t
        for m in ziele:
            _binde(m, shim_dt, shim_t)
        yield instant
    finally:
        if alt_fremd is None:
            os.environ.pop("FFC_FREMD_UHR", None)
        else:
            os.environ["FFC_FREMD_UHR"] = alt_fremd
        for key, wert in alt_sys.items():
            if wert is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = wert
        for m, namen in alt_namen:
            for name, wert in namen.items():
                setattr(m, name, wert)


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


def trap_modul(modul: str, offset_tage: int, discover: bool = False,
               modus: str = MODUS_VERSCHOBEN) -> int:
    """Unit-Test-MODUL (oder ein Testverzeichnis) unter fremder Uhr ausführen.

    Gegenstück zu `trap()` für `scripts/tests/`: Dessen Fixtures kommen oft von
    der echten Wanduhr, während die geprüfte Logik ein gepinntes Datum erwartet.
    Genau diese Mischung legte am 01.10.2026 die Publication-Reliability-Prüfung
    lahm (`test_social_perf_feedback` baute „veröffentlicht = JETZT minus 2 Tage"
    und plante dann für den 14.09.2026 – drei Wochen später war kein Slot mehr
    erreichbar). Als `--selftest`-Skript wäre das sofort aufgefallen; als
    Testmodul lief es unter dem Radar, weil die Uhr-Probe nur Skripte kannte.

    `discover=True` nimmt ein VERZEICHNIS (`scripts/tests`): dann läuft die
    gesamte Fundstelle unter der fremden Uhr – der Beweis, dass die Suite an
    jedem Kalendertag grün ist, nicht nur an dem, an dem sie geschrieben wurde.

    Rückgabe: 0 = grün · 1 = Datumsabhängigkeit gefunden · 2 = Probe nicht
    lauffähig (Import-/Sammelfehler). Die Unterscheidung ist keine Kosmetik:
    Eine Probe, die ihr Ziel nicht laden kann, ist kein Datumsbefund – sie würde
    sonst einen Fehlalarm erzeugen und den echten Befund verwässern.
    """
    import unittest

    # Dieselbe Falle wie in `trap()`: `python3 scripts/selftest_clock.py` legt
    # nur `scripts/` auf sys.path. Ohne die folgenden Zeilen scheitert schon der
    # Import von `scripts.tests.…` – und der Trap schlüge Alarm, obwohl nichts
    # datumsabhängig ist (selbst erlebt beim Einbau am 07.10.2026).
    hier = os.path.dirname(os.path.abspath(__file__))
    for kandidat in (hier, os.path.dirname(hier), os.getcwd()):
        if kandidat and kandidat not in sys.path:
            sys.path.insert(0, kandidat)
    instant = (_echt_dt.datetime.now(_echt_dt.timezone.utc)
               + _echt_dt.timedelta(days=offset_tage, hours=3, minutes=7))
    loader = unittest.TestLoader()
    # Frisch laden: Die Uhr wirkt nur beim IMPORT – ein bereits importiertes
    # Modul hielte die echte `datetime`-Referenz fest und die Probe wäre blind
    # (genau das zeigte der eigene Selbsttest beim zweiten Aufruf). In der CI
    # läuft je Probe ein eigener Prozess; innerhalb eines Prozesses räumt das hier auf.
    if discover:
        for name in [n for n in sys.modules
                     if n.startswith("test_") or n.startswith("scripts.tests")]:
            sys.modules.pop(name, None)
    else:
        for name in [modul] + [n for n in sys.modules if n.startswith(modul + ".")]:
            sys.modules.pop(name, None)
    with uhr(instant, modus):
        if discover:
            start = os.path.abspath(modul)
            if start not in sys.path:
                sys.path.insert(0, start)
            suite = loader.discover(start, pattern="test_*.py")
        else:
            suite = loader.loadTestsFromName(modul)
        ergebnis = unittest.TextTestRunner(verbosity=1).run(suite)
    # NICHT über `suite` laufen: `TextTestRunner.run()` räumt die Suite auf
    # (Tests werden durch None ersetzt) – die Prüfung muss über das Ergebnis
    # gehen. Auch das war ein eigener Fehlversuch am 07.10.2026.
    kaputt = [t for t, _ in ergebnis.errors + ergebnis.failures
              if type(t).__name__ == "_FailedTest"]
    if kaputt:
        for t in kaputt:
            print(f"🛑 Probe nicht lauffähig: {t}")
        return 2
    return 0 if ergebnis.wasSuccessful() else 1


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
        dummy.dt_alias = _echt_dt          # `import datetime as dt` – der reale Fall
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
        if dummy.dt_alias is not _echt_dt:
            fehler.append("module=…: Alias-Import (`import datetime as dt`) wurde "
                          "nicht zurückgestellt")
        with uhr(probe, MODUS_VERSCHOBEN, module=[dummy]):
            if dummy.dt_alias is _echt_dt:
                fehler.append("module=…: Alias-Import (`import datetime as dt`) "
                              "wird nicht umgebogen – der Modulname heißt nicht "
                              "`datetime`")
        # Verschachtelte Uhr: ein Modul, das erst unter der ÄUSSEREN Uhr
        # importiert wurde, hält den äußeren Shim – auch der muss weichen.
        aussen = _shim_datum(probe, MODUS_VERSCHOBEN)
        dummy2 = types.ModuleType("dummy_wache_aussen")
        dummy2.dt = aussen
        innen2 = _echt_dt.datetime(2027, 2, 1, 12, tzinfo=_echt_dt.timezone.utc)
        with uhr(innen2, MODUS_VERSCHOBEN, module=[dummy2]):
            if dummy2.dt is aussen:
                fehler.append("module=…: äußerer Shim wird nicht umgebogen – "
                              "eine verschachtelte Uhr wirkt nicht")
            if dummy2.dt.date.today() != innen2.date():
                fehler.append("module=…: verschachtelte Uhr liefert nicht den "
                              "inneren Zeitpunkt")

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

        # 6) trap_modul: findet dieselbe Bombe als TESTMODUL – und schweigt bei
        #    einem festen Modul. Der reale Fall (test_social_perf_feedback) war
        #    ein Testmodul, kein Skript; ohne diese Probe bliebe die Lücke offen.
        modul_dir = os.path.join(tmp, "modulprobe")
        os.makedirs(modul_dir, exist_ok=True)
        os.environ["MODUL_BOMBE_GRENZE"] = (_echt_dt.date.today()
                                            + _echt_dt.timedelta(days=2)).isoformat()
        with open(os.path.join(modul_dir, "test_bombe_mod.py"), "w",
                  encoding="utf-8") as fh:
            fh.write("import datetime, os, unittest\n"
                     "class BombeTest(unittest.TestCase):\n"
                     "    def test_grenze(self):\n"
                     "        grenze = datetime.date.fromisoformat(\n"
                     "            os.environ['MODUL_BOMBE_GRENZE'])\n"
                     "        self.assertGreater(grenze, datetime.date.today())\n")
        with open(os.path.join(modul_dir, "test_fest_mod.py"), "w",
                  encoding="utf-8") as fh:
            fh.write("import datetime, unittest\n"
                     "class FestTest(unittest.TestCase):\n"
                     "    def test_abstand(self):\n"
                     "        ref = datetime.date(2026, 9, 12)\n"
                     "        self.assertEqual((ref - datetime.date(2026, 8, 16)).days, 27)\n")
        sys.path.insert(0, modul_dir)
        try:
            if trap_modul("test_fest_mod", 1461) != 0:
                fehler.append("trap_modul meldet ein festes Testmodul fälschlich")
            if trap_modul("test_bombe_mod", 0) != 0:
                fehler.append("Modul-Bombe ist schon ohne Uhr-Verschiebung rot")
            if trap_modul("test_bombe_mod", 97) == 0:
                fehler.append("trap_modul lässt ein datumsabhängiges Testmodul "
                              "bei kleinem Offset grün durch")
            if trap_modul("test_bombe_mod", 1461) == 0:
                fehler.append("trap_modul lässt ein datumsabhängiges Testmodul "
                              "grün durch")
            if trap_modul(modul_dir, 0, discover=True) != 0:
                fehler.append("trap_modul(discover) ist unter der echten Uhr rot")
            if trap_modul(modul_dir, 1461, discover=True) == 0:
                fehler.append("trap_modul(discover) findet die Bombe im "
                              "Verzeichnis nicht")
            # Ein unladbares Modul ist ein Probe-Fehler (2), kein Datumsbefund (1).
            if trap_modul("gibt_es_nicht_xyz", 97) != 2:
                fehler.append("trap_modul verwechselt einen Importfehler mit "
                              "einem Datumsbefund (Rückgabe muss 2 sein)")
        finally:
            sys.path.remove(modul_dir)
            sys.modules.pop("test_bombe_mod", None)
            sys.modules.pop("test_fest_mod", None)
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
          "absolutes Dateialter (5 Tage + 5 Zeitzonen), Trap findet Zeitbomben "
          "in Skripten UND Testmodulen (discover inklusive).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Determinismus-Garantie für Selbsttests")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--trap", metavar="SCRIPT", help="Selbsttest eines Skripts unter fremder Uhr")
    ap.add_argument("--trap-modul", metavar="MODUL",
                    help="Unit-Test-Modul unter fremder Uhr (z. B. scripts.tests.test_x)")
    ap.add_argument("--trap-discover", metavar="VERZEICHNIS",
                    help="ganzes Testverzeichnis unter fremder Uhr (z. B. scripts/tests)")
    ap.add_argument("--offset", type=int, default=1461, help="Tage in die Zukunft (Standard 1461)")
    ap.add_argument("--selftest-args", default="--selftest")
    ap.add_argument("--strikt", action="store_true",
                    help="Trap-Modus: jede echte Uhr-Zeitlesung ist ein Fehler")
    args = ap.parse_args()
    if args.trap_modul or args.trap_discover:
        was = args.trap_modul or args.trap_discover
        code = trap_modul(was, args.offset, discover=bool(args.trap_discover),
                          modus=MODUS_STRIKT if args.strikt else MODUS_VERSCHOBEN)
        if code == 2:
            print(f"🛑 {was}: Uhr-Probe nicht lauffähig (Import-/Sammelfehler) – "
                  "das ist kein Datumsbefund, sondern eine kaputte Probe.")
            return 2
        if code:
            print(f"🛑 {was} ist datumsabhängig (Uhr um {args.offset} Tage "
                  f"vorgestellt, Exit {code}).")
            return 1
        print(f"✅ {was}: bleibt unter einer um {args.offset} Tage vorgestellten "
              "Uhr grün.")
        return 0
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
