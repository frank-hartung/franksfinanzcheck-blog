"""Nur explizit verkettete Folgeentscheidungen sind gültig."""
import tempfile
import unittest
from pathlib import Path
import yaml
from scripts import faktenfrische_befund_ledger as ledger


class KetteTest(unittest.TestCase):
    def test_verkettung_fail_closed(self):
        basis = dict(slug='seite', befund_id='F4', entschieden_von='Redaktion',
                     begruendung='Ein ausreichend langer begründeter Prüfvermerk.',
                     befund_fassung='a' * 64, geprueft_fassung='b' * 64)
        folge = dict(basis, geprueft_fassung='c' * 64, folgeentscheidung=True,
                     vorgaenger_geprueft_fassung='b' * 64)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'entscheidungen.yaml'
            def schreiben(items):
                path.write_text(yaml.safe_dump({'entscheidungen': items}), encoding='utf-8')
            schreiben([basis, folge])
            self.assertEqual(ledger.entscheidungen_laden(path)[('seite', 'F4')]['geprueft_fassung'], 'c' * 64)
            for kaputt in (dict(folge, vorgaenger_geprueft_fassung='d' * 64),
                           dict(folge, folgeentscheidung=False), basis):
                schreiben([basis, kaputt])
                with self.assertRaises(ledger.LedgerFehler):
                    ledger.entscheidungen_laden(path)
            schreiben([folge])
            with self.assertRaises(ledger.LedgerFehler):
                ledger.entscheidungen_laden(path)
