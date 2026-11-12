"""Offline-Sabotageproben: niemals echte Netzaufrufe oder Produktionsschreibzugriffe."""
import copy
import json
import sys
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts'))
import blog_header_gate as header
import cloudflare_edge_freigabe as edge
import live_selbstheilung as heal


def messung(gut=False):
    kopf = dict(header.GUTE_KOPFZEILEN) if gut else {}
    kopf.update(header.PROXY_KENNUNG)
    code, bericht, daten = header.netz_pruefen(
        holen=lambda *_: (200, kopf), pausen=(), schlaf=lambda _: None)
    daten['bericht'] = bericht
    # Der Gegenmessungsfall isoliert die fachliche Datenschutzprüfung.
    if gut:
        daten['abschluss_blocker'] = []
    return code, daten


class Heilvertrag(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = Path(self.tmp.name) / 'audit.jsonl'
        self.b7 = Path(self.tmp.name) / 'b7.md'
        self.b7.write_text('\n'.join([edge.B7_MIT_PROXY_SATZ, edge.B7_TABELLE_NEU,
                                      edge.B7_DIENSTLEISTER_NEU]), encoding='utf8')
        self.api = Mock(return_value=(1, 'offen'))
        self.apply = Mock(return_value=(0, 'soll'))
        code, daten = messung(True)
        self.live = Mock(return_value=(code, daten['bericht'], daten))
        self.code, self.daten = messung()

    def run_heal(self, **kw):
        args = dict(daten=self.daten, code=self.code, token='test-only-token',
                    freigabe='true', ledger=self.ledger, api_pruefen=self.api,
                    anwenden=self.apply, live_messen=self.live, b7_pfad=self.b7)
        args.update(kw)
        return heal.ausfuehren(**args)

    def events(self):
        return [json.loads(line) for line in self.ledger.read_text().splitlines()]

    def test_repariert_einmal_und_misst_wirkung_ohne_den_ursprungsnachweis_zu_veraendern(self):
        vorher = copy.deepcopy(self.daten)
        self.assertEqual(self.run_heal()[0], 0)
        self.assertEqual(self.daten, vorher)
        self.api.assert_called_once_with('test-only-token', heal.ZONE)
        self.apply.assert_called_once_with('test-only-token', heal.ZONE, b7=False)
        self.live.assert_called_once()
        self.assertEqual([e['status'] for e in self.events()],
                         ['start', 'vorher', 'api_vorher', 'aenderung_begonnen', 'api_nachher', 'live_nachher', 'gegenmessung_ok'])
        self.assertNotIn('test-only-token', self.ledger.read_text())

    def test_kein_token_oder_keine_freigabe(self):
        for token, consent in [('', 'true'), ('x', ''), ('x', 'TRUE')]:
            self.assertEqual(self.run_heal(token=token, freigabe=consent)[0], heal.POLICY_BLOCKED)
        self.api.assert_not_called()
        self.apply.assert_not_called()

    def test_b7_schranke_fail_closed(self):
        for text in ['', 'kein Proxy von Cloudflare', edge.B7_MIT_PROXY_SATZ]:
            self.b7.write_text(text, encoding='utf8')
            self.assertEqual(self.run_heal()[0], heal.POLICY_BLOCKED)
        self.b7.unlink()
        self.assertEqual(self.run_heal()[0], heal.POLICY_BLOCKED)
        self.api.assert_not_called()

    def test_klassen_und_ungueltige_messung_heilen_nie(self):
        code, good = messung(True)
        self.assertEqual(self.run_heal(daten=good, code=code)[0], 0)
        for d, c in [({}, 1), (self.daten, 0), ({**self.daten, 'klasse': 'STOERUNG'}, 2),
                     ({**self.daten, 'klasse': 'TEILWEISE'}, 0)]:
            self.assertEqual(self.run_heal(daten=d, code=c)[0], 2)
        def teilweise(url, weg):
            if url == header.ZIELE[1]:
                raise OSError('offline')
            return 200, {**header.GUTE_KOPFZEILEN, **header.PROXY_KENNUNG}
        for holen in (teilweise, lambda *_: (_ for _ in ()).throw(OSError('offline'))):
            c, bericht, d = header.netz_pruefen(holen=holen, pausen=(), schlaf=lambda _: None)
            d['bericht'] = bericht
            self.assertIn(d['klasse'], ('TEILWEISE', 'STOERUNG'))
            self.assertEqual(self.run_heal(daten=d, code=c)[0], 2)
        self.apply.assert_not_called()

    def test_fremde_oder_teilweise_ziele_niemals_heilen(self):
        for changes in [dict(nicht_gemessen=['x']), dict(stoerung=['x']),
                        dict(ziele=[]), dict(gemessen=1),
                        dict(ziele=[{'url': 'https://evil.invalid', 'klasse': 'GEMESSEN'}]*2)]:
            self.assertEqual(self.run_heal(daten={**self.daten, **changes})[0], 2)
        self.api.assert_not_called()

    def test_api_soll_oder_stoerung_keine_aenderung(self):
        for code in [0, 2, 99]:
            self.api.return_value = (code, '')
            self.assertNotEqual(self.run_heal()[0], 0)
        self.apply.assert_not_called()

    def test_schreibfehler_und_teilheilung_bleiben_rot_und_ohne_secret(self):
        self.apply.side_effect = RuntimeError('test-only-token')
        code, text = self.run_heal()
        self.assertEqual(code, 2)
        self.assertNotIn('test-only-token', text)
        self.assertEqual(self.events()[-2]['status'], 'aenderung_begonnen')
        self.live.assert_not_called()

    def test_nachmessung_muss_vollstaendig_sein(self):
        self.live.return_value = (self.code, self.daten['bericht'], self.daten)
        self.assertEqual(self.run_heal()[0], 1)
        self.assertEqual(self.events()[-1]['status'], 'live_nicht_soll')
        code, good = messung(True)
        good['ziele'][0]['status'] = 503
        self.live.return_value = (code, good['bericht'], good)
        self.assertEqual(self.run_heal()[0], 2)
        self.apply.return_value = (1, 'offen')
        self.assertEqual(self.run_heal()[0], 1)

    def test_audit_fehler_verhindert_schreiben(self):
        with self.assertRaises(OSError):
            self.run_heal(ledger=Path(self.tmp.name) / 'fehlt' / 'audit')
        self.api.assert_not_called()
        self.apply.assert_not_called()


class Verdrahtung(unittest.TestCase):
    def test_workflow_schuetzt_live_schreibpfad_und_nachweis(self):
        text = (ROOT / '.github/workflows/sicherheits-wache.yml').read_text(encoding='utf8')
        self.assertEqual(text.count('"scripts/live_selbstheilung.py"'), 2)
        self.assertEqual(text.count('"scripts/tests/test_live_selbstheilung.py"'), 2)
        nachweis = text.index('- name: Live-Nachweis abschließen')
        heilung = text.index('- name: F-01 kontrolliert selbstheilen')
        artefakt = text.index('- name: Sicherheits-Nachweise aufbewahren')
        self.assertLess(nachweis, heilung)
        self.assertLess(heilung, artefakt)
        block = text[heilung:artefakt]
        self.assertIn("github.ref == 'refs/heads/main'", block)
        self.assertIn("steps.header.outcome == 'success'", block)
        self.assertIn('secrets.CF_EDGE_HEAL_TOKEN', block)
        self.assertIn('vars.CF_EDGE_AUTOHEAL', block)
        self.assertIn('f01-heilung.jsonl', text[artefakt:])
        self.assertIn('scripts.tests.test_live_selbstheilung', text)

    def test_cli_widerspruch_zwischen_json_und_bericht_verhindert_heilung(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, daten = messung()
            root = Path(tmp)
            (root / 'daten').write_text(json.dumps(daten), encoding='utf8')
            (root / 'bericht').write_text('anderer Bericht', encoding='utf8')
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/live_selbstheilung.py'),
                                     '--run', '--daten', str(root / 'daten'),
                                     '--bericht', str(root / 'bericht'), '--code', '1',
                                     '--ledger', str(root / 'audit')],
                                    capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(result.returncode, 2)
            self.assertFalse((root / 'audit').exists())

    def test_cli_fehlende_freigabe_ist_warnung_und_keine_zweite_jobstoerung(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _, daten = messung()
            (root / 'daten').write_text(json.dumps(daten), encoding='utf8')
            (root / 'bericht').write_text(daten['bericht'], encoding='utf8')
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/live_selbstheilung.py'),
                                     '--run', '--daten', str(root / 'daten'),
                                     '--bericht', str(root / 'bericht'), '--code', '1',
                                     '--ledger', str(root / 'audit')],
                                    capture_output=True, text=True, cwd=ROOT,
                                    env={'GITHUB_STEP_SUMMARY': str(root / 'summary')})
            self.assertEqual(result.returncode, 0)
            self.assertIn('::warning title=F-01 Selbstheilung nicht freigegeben::', result.stdout)
            self.assertIn('CF_EDGE_HEAL_TOKEN', result.stdout)
            self.assertEqual(json.loads((root / 'audit').read_text().splitlines()[-1])['status'],
                             'freigabe_fehlt')
            self.assertIn('absichtliche Schutzschranke', (root / 'summary').read_text())

    def test_cli_fehlt_messung_schreibt_nicht(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, str(ROOT / 'scripts/live_selbstheilung.py'),
                                     '--run', '--daten', str(Path(tmp) / 'fehlt'),
                                     '--bericht', str(Path(tmp) / 'bericht'),
                                     '--code', '1', '--ledger', str(Path(tmp) / 'audit')],
                                    capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(result.returncode, 2)
            self.assertFalse((Path(tmp) / 'audit').exists())


if __name__ == '__main__':
    unittest.main()
