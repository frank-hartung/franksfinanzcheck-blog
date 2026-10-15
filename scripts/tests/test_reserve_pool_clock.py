"""Regression #759: Selbsttests dürfen nicht an UTC-Mitternacht kippen.

Der Veröffentlichungsstempel liegt absichtlich eine Minute zurück. Zwischen
00:00:00 und 00:00:59 gehört er zum Vortag; die Produktionssperre verweigert
korrekt die Rückdatierung. Ein Selbsttest braucht deshalb eine eigene,
konsistente Uhr, nicht sieben künstliche Publikationstage.
"""
import contextlib
import datetime as dt
import io
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import reserve_pool as rp
import reserve_topics as topics
import selftest_clock as clock

CLOCK_MODULES = (rp, rp.cadence_guard, rp.cadence_guard.park_state,
                 rp.artifacts, topics)


def instant(stamp):
    return dt.datetime.fromisoformat(stamp)


class ReserveSelftestClockTests(unittest.TestCase):
    def run_at(self, stamp, mode=clock.MODUS_VERSCHOBEN):
        output = io.StringIO()
        with clock.uhr(instant(stamp), mode, module=CLOCK_MODULES), \
                contextlib.redirect_stdout(output):
            errors = rp.run_selftest()
        self.assertEqual(errors, [], output.getvalue())
        return output.getvalue()

    def test_midnight_boundaries_have_identical_results(self):
        reference = self.run_at("2026-10-15T12:00:00+00:00")
        for stamp in (
            "2026-10-14T23:59:59+00:00",
            "2026-10-15T00:00:00+00:00",
            "2026-10-15T00:00:30+00:00",
            "2026-10-15T00:00:43+00:00",  # Meldungszeitpunkt #759
            "2026-10-15T00:00:59+00:00",
            "2026-10-15T00:01:00+00:00",
        ):
            with self.subTest(stamp=stamp):
                self.assertEqual(self.run_at(stamp), reference)

    def test_weekdays_calendar_boundaries_and_timezones(self):
        reference = self.run_at("2026-09-28T12:00:00+00:00")
        stamps = [f"2026-10-{day:02d}T00:00:30+00:00"
                  for day in range(12, 19)]  # alle sieben Wochentage
        stamps += [
            "2026-11-01T00:00:30+00:00",  # Monatswechsel
            "2027-01-01T00:00:30+00:00",  # Jahreswechsel
            "2028-02-29T00:00:30+00:00",  # Schalttag
            "2028-03-01T00:00:30+00:00",
            "2030-10-15T00:00:30+00:00",
            "2026-10-15T00:00:30+14:00",  # lokaler Tag != UTC-Tag
            "2026-10-15T23:59:59-12:00",
        ]
        for stamp in stamps:
            with self.subTest(stamp=stamp):
                self.assertEqual(self.run_at(stamp), reference)

    def test_selftest_never_reads_the_outer_wall_clock(self):
        self.run_at("2031-05-04T00:00:30+00:00", clock.MODUS_STRIKT)

    def test_real_publication_logic_runs_on_an_unmodified_publication_day(self):
        original_publish = rp.publish_to_min
        original_days = rp.cadence_guard.PUBLICATION_DAYS
        observations = []

        def observe(*args, **kwargs):
            day = rp.datetime.date.today()
            stamp = rp.now_utc_iso()
            self.assertIs(rp.cadence_guard.PUBLICATION_DAYS, original_days)
            self.assertIn(day.weekday(), original_days)
            self.assertEqual(stamp[:10], day.isoformat())
            result = original_publish(*args, **kwargs)
            observations.append((day, stamp, result))
            return result

        with patch.object(rp, "publish_to_min", side_effect=observe):
            self.run_at("2026-10-15T00:00:30+00:00")
        self.assertEqual(len(observations), 2)
        self.assertEqual(observations[0][2], ["pool-stromfresser-a"])
        self.assertEqual(observations[1][2], [])
        self.assertEqual(observations[0][:2], observations[1][:2])

    def test_clock_root_and_environment_restored_even_after_failure(self):
        for fail in (False, True):
            with self.subTest(fail=fail), \
                    clock.uhr(instant("2030-01-01T00:00:30+00:00"),
                              module=CLOCK_MODULES):
                old_bindings = [(m, getattr(m, "datetime", None),
                                 getattr(m, "dt", None)) for m in CLOCK_MODULES]
                old_sys_clock = (sys.modules["datetime"], sys.modules["time"])
                old_env = dict(os.environ)
                old_root = rp.ROOT
                old_days = rp.cadence_guard.PUBLICATION_DAYS
                with contextlib.redirect_stdout(io.StringIO()):
                    if fail:
                        with patch.object(rp, "publish_to_min",
                                          side_effect=RuntimeError("Testabbruch")), \
                                self.assertRaisesRegex(RuntimeError, "Testabbruch"):
                            rp.run_selftest()
                    else:
                        self.assertEqual(rp.run_selftest(), [])
                for module, date_binding, dt_binding in old_bindings:
                    self.assertIs(getattr(module, "datetime", None), date_binding)
                    self.assertIs(getattr(module, "dt", None), dt_binding)
                self.assertIs(sys.modules["datetime"], old_sys_clock[0])
                self.assertIs(sys.modules["time"], old_sys_clock[1])
                self.assertEqual(dict(os.environ), old_env)
                self.assertIs(rp.ROOT, old_root)
                self.assertIs(rp.cadence_guard.PUBLICATION_DAYS, old_days)

    def test_selftest_does_not_read_production_certificates(self):
        # Ein vorhandenes Zertifikat darf weder Fixtures priorisieren noch
        # einen weiteren, von der Produktionsuhr abhängigen Lesepfad öffnen.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cert = root / "data" / "reserve-readiness.json"
            cert.parent.mkdir()
            cert.write_text("Produktionsnachweis – nicht für Fixtures", encoding="utf-8")
            before = cert.read_bytes()
            with patch.object(rp, "ROOT", root), \
                    patch.object(rp.artifacts, "read_certificate",
                                 side_effect=AssertionError("Produktionszertifikat gelesen")):
                self.run_at("2026-10-15T12:00:00+00:00")
            self.assertEqual(cert.read_bytes(), before)
            self.assertEqual(list(root.rglob("*.json")), [cert])

    def test_broken_publication_is_still_reported(self):
        with patch.object(rp, "publish_to_min", return_value=[]), \
                contextlib.redirect_stdout(io.StringIO()):
            errors = rp.run_selftest()
        self.assertTrue(any("Ein-Thema-Pool" in error for error in errors), errors)

    def test_reported_success_needs_a_validator_and_a_live_article(self):
        with patch.object(rp, "publish_to_min",
                          side_effect=[["pool-stromfresser-a"], []]), \
                contextlib.redirect_stdout(io.StringIO()):
            errors = rp.run_selftest()
        self.assertTrue(any("nicht durch Validator und LIVE-Bestand belegt" in error
                            for error in errors), errors)

    def test_missing_topic_lock_is_still_reported(self):
        with patch.object(rp, "sperr_treffer", return_value=None), \
                contextlib.redirect_stdout(io.StringIO()):
            errors = rp.run_selftest()
        self.assertTrue(any("Dublette" in error for error in errors), errors)

    def test_disabled_publication_calendar_is_not_overridden(self):
        with patch.object(rp.cadence_guard, "PUBLICATION_DAYS", set()), \
                contextlib.redirect_stdout(io.StringIO()):
            errors = rp.run_selftest()
        self.assertTrue(any("Ein-Thema-Pool" in error for error in errors), errors)

    def test_cli_at_midnight_and_under_strict_clock(self):
        # Frischer Prozess: deckt den __main__-Pfad ab, nicht nur den Import.
        code = """
import datetime as dt
import runpy
import sys
sys.path.insert(0, 'scripts')
from selftest_clock import uhr
mode = sys.argv[1]
sys.argv = ['scripts/reserve_pool.py', '--selftest']
with uhr(dt.datetime(2026, 10, 15, 0, 0, 30, tzinfo=dt.timezone.utc), mode):
    runpy.run_path('scripts/reserve_pool.py', run_name='__main__')
"""
        for mode in (clock.MODUS_VERSCHOBEN, clock.MODUS_STRIKT):
            with self.subTest(mode=mode):
                result = subprocess.run(
                    [sys.executable, "-c", code, mode], cwd=SCRIPTS.parent,
                    text=True, capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn("Reserve-Pool-Selbsttest grün", result.stdout)


class ReservePublicationBoundaryTests(unittest.TestCase):
    """Produktionsschutz bleibt scharf; kein Aufweichen für grüne Tests."""

    def setUp(self):
        tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.root = Path(tmp)
        self.enterContext(patch.object(rp, "ROOT", self.root))
        self.posts = self.root / "content" / "posts"
        self.path = self.posts / "reserve-strom" / "index.md"
        self.path.parent.mkdir(parents=True)
        self.path.write_text(
            '---\ntitle: "Stromfresser finden: Der Messplan"\n'
            'date: 2026-09-01T06:00:00Z\ndraft: true\nreserve: true\n'
            '---\n\nUnveränderter Artikel.\n', encoding="utf-8")
        self.original = self.path.read_bytes()

    def publish_at(self, stamp, validator):
        with clock.uhr(instant(stamp), module=CLOCK_MODULES), \
                contextlib.redirect_stdout(io.StringIO()):
            return rp.publish_to_min(posts_dir=self.posts, validator=validator)

    def test_first_utc_minute_never_backdates_a_publication(self):
        for second in (0, 30, 59):
            with self.subTest(second=second):
                validator = Mock(return_value=True)
                result = self.publish_at(
                    f"2026-09-28T00:00:{second:02d}+00:00", validator)
                self.assertEqual(result, [])
                validator.assert_not_called()
                self.assertEqual(self.path.read_bytes(), self.original)

    def test_publication_resumes_at_the_first_safe_second(self):
        validator = Mock(return_value=True)
        result = self.publish_at("2026-09-28T00:01:00+00:00", validator)
        self.assertEqual(result, ["reserve-strom"])
        validator.assert_called_once_with(self.path)
        text = self.path.read_text(encoding="utf-8")
        self.assertIn("date: 2026-09-28T00:00:00Z", text)
        self.assertIn("draft: false", text)
        self.assertIn("reserve_published: 2026-09-28", text)
        self.assertNotIn("reserve: true", text)

    def test_only_monday_wednesday_friday_can_publish(self):
        monday = dt.date(2026, 9, 28)
        for offset in range(7):
            day = monday + dt.timedelta(days=offset)
            with self.subTest(day=day):
                self.path.write_bytes(self.original)
                validator = Mock(return_value=True)
                result = self.publish_at(f"{day}T12:00:00+00:00", validator)
                if offset in (0, 2, 4):
                    self.assertEqual(result, ["reserve-strom"])
                    validator.assert_called_once_with(self.path)
                else:
                    self.assertEqual(result, [])
                    validator.assert_not_called()
                    self.assertEqual(self.path.read_bytes(), self.original)

    def test_rollover_to_the_next_day_keeps_the_candidate_untouched(self):
        validator = Mock(return_value=True)
        with patch.object(rp, "now_utc_iso", return_value="2026-09-29T00:00:00Z"):
            result = self.publish_at("2026-09-28T23:59:59+00:00", validator)
        self.assertEqual(result, [])
        validator.assert_not_called()
        self.assertEqual(self.path.read_bytes(), self.original)


if __name__ == "__main__":
    unittest.main()
