"""Versandvertrag unabhängig von Systemzeit/Netz: Kalender, Journal, echter Sendepfad."""
import datetime as dt
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import newsletter_schedule as ns
import newsletter_digest as nd
import newsletter_cadence as nc

ROOT = Path(__file__).resolve().parents[2]


def zeit(tag, stunde=7):
    return dt.datetime.fromisoformat(f"{tag}T{stunde:02}:05:00+02:00")


class Kalender(unittest.TestCase):
    def test_exakt_zwei_versandtage(self):
        start = zeit("2026-09-21")
        erlaubt = [i for i in range(7) if not ns.versandpause({}, start + dt.timedelta(days=i))]
        self.assertEqual([1, 4], erlaubt)

    def test_zweiter_lauf_am_selben_tag_bleibt_aus(self):
        self.assertIn("bereits", ns.versandpause(
            {"versand_termine": [zeit("2026-09-22").isoformat()]}, zeit("2026-09-22", 12)))

    def test_wochenlimit_auch_mit_altem_werktagsversand(self):
        state = {"versand_termine": [zeit("2026-09-21").isoformat(), zeit("2026-09-22").isoformat()]}
        self.assertIn("Kalenderwoche", ns.versandpause(state, zeit("2026-09-25")))
        self.assertEqual("", ns.versandpause(state, zeit("2026-09-29")))

    def test_jahreswechsel_iso_woche(self):
        state = {"versand_termine": ["2026-12-29T07:00:00+01:00", "2026-12-30T07:00:00+01:00"]}
        self.assertIn("Kalenderwoche", ns.versandpause(state, dt.datetime.fromisoformat("2027-01-01T07:00:00+01:00")))

    def test_sommer_und_winterzeit_berlin(self):
        for tag in ("2026-03-31", "2026-10-27"):
            with self.subTest(tag=tag):
                self.assertEqual("", ns.versandpause({}, dt.datetime.fromisoformat(tag + "T05:05:00+00:00")))
        # UTC-Montag, in Berlin bereits Dienstag: lokaler Kalendertag entscheidet.
        self.assertEqual("", ns.versandpause({}, dt.datetime.fromisoformat("2026-09-21T22:05:00+00:00")))

    def test_migration_und_kaputtes_journal(self):
        self.assertIn("bereits", ns.versandpause({"zuletzt_versandt": zeit("2026-09-22").isoformat()}, zeit("2026-09-22", 9)))
        for wert in (None, {}, ["kaputt"], ["2026-09-22T07:00:00"], ["2027-01-01T07:00:00+01:00"]):
            with self.subTest(wert=wert), self.assertRaises((ValueError, TypeError)):
                ns.versandpause({"versand_termine": wert}, zeit("2026-09-22"))

    def test_wache_nur_an_versandtagen_und_nach_faelligkeit(self):
        for tag in ("2026-09-21", "2026-09-23", "2026-09-24", "2026-09-26", "2026-09-27"):
            self.assertEqual("ruhetag", nc.entscheide([], zeit(tag, 12))["handlung"])
        self.assertEqual("ruhetag", nc.entscheide([], zeit("2026-09-22"))["handlung"])
        self.assertEqual("nachholen", nc.entscheide([], zeit("2026-09-22", 12))["handlung"])

    def test_workflows_und_nachholen_haben_dieselbe_kadenz(self):
        for name, cron in (("newsletter-daily.yml", '5 5 * * 2,5'), ("newsletter-cadence.yml", '11 8 * * 2,5')):
            self.assertIn(f'cron: "{cron}"', (ROOT / '.github/workflows' / name).read_text())
        with patch.object(nc, '_gh') as gh:
            gh.return_value.returncode = 0
            nc.hole_nach('org/repo', 'branch')
            self.assertIn('tage=7', gh.call_args.args[0])


class Versandpfad(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        nd.speichere_state(self.root, {})
        self.env = patch.dict('os.environ', {'BREVO_API_KEY': 'test-key', 'BREVO_LIST_ID': '1', 'NEWSLETTER_SEND': 'ja'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def senden(self, **kw):
        return nd.versende(self.root, '<p>Test</p>', 'Test', 'Test', dry_run=False, **kw)

    def test_ruhetag_hat_keinen_netzaufruf(self):
        with patch.object(ns, 'jetzt', return_value=zeit('2026-09-23')), patch.object(nd, 'TRANSPORT') as post, patch.object(nd, 'TRANSPORT_GET') as get:
            self.assertEqual(0, self.senden())
            post.assert_not_called()
            get.assert_not_called()

    def test_reservierung_vor_sendnow_und_doppelaufruf(self):
        def transport(key, pfad, body):
            if pfad.endswith('/sendNow'):
                self.assertEqual(1, len(nd.lade_state(self.root)['versand_termine']))
                return 204, ''
            return 201, '{"id": 123}'
        with patch.object(ns, 'jetzt', return_value=zeit('2026-09-22')), patch.object(nd, 'vorflug', return_value=(0, 'ok')), patch.object(nd, 'TRANSPORT', side_effect=transport) as post:
            self.assertEqual(0, self.senden())
            self.assertEqual(0, self.senden())
            self.assertEqual(2, post.call_count)  # create + sendNow, keine zweite Kampagne

    def test_schreibfehler_verhindert_sendnow(self):
        with patch.object(ns, 'jetzt', return_value=zeit('2026-09-22')), patch.object(nd, 'vorflug', return_value=(0, 'ok')), patch.object(nd, 'TRANSPORT', return_value=(201, '{"id": 123}')) as post, patch.object(nd, 'speichere_state', side_effect=OSError('voll')):
            self.assertEqual(1, self.senden())
            self.assertEqual(['emailCampaigns'], [c.args[1] for c in post.call_args_list])

    def test_defekter_oder_fehlender_status_sperrt(self):
        pfad = Path(self.root) / nd.STATE_REL
        for text in ('{kaputt', 'null', '[]'):
            pfad.write_text(text)
            with patch.object(nd, 'TRANSPORT') as post:
                self.assertEqual(1, self.senden())
                post.assert_not_called()
        pfad.unlink()
        with patch.object(nd, 'TRANSPORT') as post:
            self.assertEqual(1, self.senden())
            post.assert_not_called()

    def test_einzeltest_verbraucht_keinen_termin(self):
        with patch.object(ns, 'jetzt', return_value=zeit('2026-09-23')), patch.object(nd, 'vorflug', return_value=(0, 'ok')), patch.object(nd, 'TRANSPORT', side_effect=[(201, '{"id": 123}'), (204, '')]) as post:
            self.assertEqual(0, self.senden(test_adresse='probe@example.test'))
            self.assertTrue(post.call_args.args[1].endswith('/sendTest'))
            state = nd.lade_state(self.root)
            self.assertNotIn('versand_termine', state)
            self.assertNotIn('zuletzt_versandt', state)
            self.assertIn('zuletzt_getestet', state)
            self.assertEqual('', ns.versandpause(state, zeit('2026-09-25')))

    def test_ausgabe_enthaelt_nur_die_verbuchten_artikel(self):
        artikel = [{'slug': f'artikel-{i}'} for i in range(8)]
        with patch.object(nd.studio, 'konfiguration', return_value={'email': {'max_artikel': 5}}), patch.object(nd.studio, 'material_aus_artikel', side_effect=lambda root, a: a), patch.object(nd.studio, 'baue_email', side_effect=lambda a, **kw: {'material': a}):
            ausgabe = nd.baue_ausgabe(artikel, '2026-09-25', 'Zweimal pro Woche', root=self.root)
            self.assertEqual(5, ausgabe['anzahl'])
            self.assertEqual(artikel[:5], ausgabe['material'])
            self.assertNotIn(artikel[5], ausgabe['material'])

    def test_cli_pause_schreibt_keinen_pending_status(self):
        vorher = (Path(self.root) / nd.STATE_REL).read_text()
        with patch.object(ns, 'jetzt', return_value=zeit('2026-09-23')), patch.object(nd, 'assert_worktree'), patch.object(nd, 'TRANSPORT') as post:
            self.assertEqual(0, nd.main(['--root', self.root, '--build', '--send', '--live', '--trotz-qa']))
            post.assert_not_called()
            self.assertEqual(vorher, (Path(self.root) / nd.STATE_REL).read_text())

    def test_vorschau_repariert_keinen_kaputten_status_stillschweigend(self):
        pfad = Path(self.root) / nd.STATE_REL
        pfad.write_text('{kaputt')
        with patch.object(nd, 'assert_worktree'):
            self.assertEqual(1, nd.main(['--root', self.root, '--build']))
        self.assertEqual('{kaputt', pfad.read_text())


if __name__ == '__main__':
    unittest.main()
