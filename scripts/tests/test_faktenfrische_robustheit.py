"""Offline-Regressionen für externe Daten und die Schreibgrenze."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import yaml
from scripts import faktenfrische as ff


class FaktenfrischeRobustheit(unittest.TestCase):
    def setUp(self):
        self.cfg = {"quellen_allowlist": [{"domain": "destatis.de", "herausgeber": "Destatis", "rang": 1}]}
        self.url = "https://www.destatis.de/test"
        self.dossier = {"treffer": [{"url": self.url, "titel": "Original", "datum": "2026-01-02", "belegfaehig": True}]}

    def test_untrusted_response_types(self):
        for response in ['{}', '{"befunde":{},"quellen":[]}', '{"befunde":[],"quellen":null}', 'nonsense']:
            self.assertIsNone(ff._antwort_daten(response))
            self.assertEqual(ff.claude_antwort_pruefen(response, self.dossier, self.cfg), ([], []))
        response = json.dumps({"befunde": [{"text": 123}, {"text": "Hinweis", "typ": [], "beleg": 9}], "quellen": [{"url": 4}]})
        self.assertIsNone(ff._antwort_daten(response))
        self.assertEqual(ff.claude_antwort_pruefen(response, self.dossier, self.cfg), ([], []))

    def test_metadata_comes_from_dossier_not_model(self):
        response = json.dumps({"befunde": [], "quellen": [{"url": self.url, "titel": "Erfunden", "datum": "2099-01-01", "herausgeber": "Fake"}]})
        _, sources = ff.claude_antwort_pruefen(response, self.dossier, self.cfg)
        self.assertEqual(sources, [{"url": self.url, "titel": "Original", "datum": "2026-01-02", "herausgeber": "Destatis"}])
        self.dossier['treffer'][0]['datum'] = ''
        self.assertEqual(ff.claude_antwort_pruefen(response, self.dossier, self.cfg)[1][0]['datum'], '')

    def test_invalid_provider_response_falls_back(self):
        art = {"titel": "Test", "beschreibung": "", "body": ""}
        good = json.dumps({"artikel_sha256": ff.ledger.pruef_hash(art),
                               "befunde": [], "quellen": []})
        with patch.object(ff, 'verfuegbare_anbieter', return_value=['a', 'b']), patch.object(ff.llm_client, 'model_for', return_value='model'), patch.object(ff.llm_client, 'chat', side_effect=['{}', good]):
            self.assertIn('geprüft (b:', ff.claude_fachpruefung(art, self.dossier, self.cfg)[2])

    def test_source_limit_and_allowlist(self):
        cfg = dict(self.cfg, budget={'max_quellen_frontmatter': 0})
        self.assertEqual(ff.quellen_aus_dossier(self.dossier, cfg), [])
        self.assertEqual(ff.claude_antwort_pruefen(json.dumps({'befunde': [], 'quellen': [{'url': self.url}]}), self.dossier, cfg)[1], [])
        self.dossier['treffer'].append(dict(self.dossier['treffer'][0], url='https://evil.example/'))
        self.assertEqual(len(ff.quellen_aus_dossier(self.dossier, self.cfg)), 1)

    def test_yaml_escaping_and_inline_replacement(self):
        sources = [{'titel': 'Zeile\n"zwei"\t\\', 'url': self.url}]
        fm = ff.fm_setze_quellen('title: Test\nquellen: []\nlastmod: 2026-01-01', sources)
        self.assertEqual(fm.count('quellen:'), 1)
        self.assertEqual(yaml.safe_load(fm)['quellen'][0]['titel'], sources[0]['titel'])
        self.assertEqual(ff.fm_setze_quellen(fm, sources), fm)

    def test_routing_spiegelt_ssot(self):
        config = yaml.safe_load((Path(ff.BLOG_DIR) / 'data/ki_transportweg.yaml').read_text(encoding='utf-8'))
        self.assertEqual(list(ff.PROVIDER_ORDER), config['routing']['faktenpruefung']['kette'])
        self.assertEqual(ff.PROVIDER_ORDER[0], 'gemini')

    def test_routing_is_loaded_and_invalid_routing_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'routing.yaml'
            path.write_text('routing:\n  faktenpruefung:\n    kette: [nvidia, gemini]\n', encoding='utf-8')
            self.assertEqual(ff.lade_provider_order(str(path)), ('nvidia', 'gemini'))
            for chain in ('[gemini]', '[gemini, unknown]', '[gemini, gemini]'):
                path.write_text(f'routing:\n  faktenpruefung:\n    kette: {chain}\n', encoding='utf-8')
                with self.assertRaises(SystemExit):
                    ff.lade_provider_order(str(path))

    def test_incomplete_transport_falls_back_and_redacts_errors(self):
        art = {"titel": "Test", "beschreibung": "", "body": ""}
        good = json.dumps({"artikel_sha256": ff.ledger.pruef_hash(art),
                               "befunde": [], "quellen": []})
        with patch.object(ff, 'verfuegbare_anbieter', return_value=['gemini', 'groq']), \
             patch.object(ff.llm_client, 'model_for', return_value='model'), \
             patch.object(ff.llm_client, 'chat', side_effect=[RuntimeError('secret'), good]) as chat:
            result = ff.claude_fachpruefung(art, self.dossier, self.cfg)
            self.assertIn('geprüft (groq:', result[2])
            self.assertTrue(chat.call_args.kwargs['require_complete'])
            self.assertFalse(chat.call_args.kwargs['log_errors'])
        with patch.object(ff, 'verfuegbare_anbieter', return_value=['gemini']), \
             patch.object(ff.llm_client, 'model_for', return_value='model'), \
             patch.object(ff.llm_client, 'chat', side_effect=RuntimeError('secret')):
            status = ff.claude_fachpruefung(art, self.dossier, self.cfg)[2]
            self.assertNotIn('secret', status)
            self.assertIn('RuntimeError', status)

    def test_apply_failure_keeps_item_in_queue(self):
        art = {'slug': 'test', 'titel': 'Test', 'beschreibung': '', 'body': '', 'faktencheck': None}
        geo = {'prozent': 0, 'offen': []}
        due = {'faellig': True, 'prio': 0, 'grund': 'neu', 'frist': None, 'restlaufzeit': None}
        dossier = dict(self.dossier, fehler=[], begriffe=[], kanaele=[], erzeugt='now')
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(ff.sys, 'argv', ['faktenfrische.py', '--apply']), \
             patch.object(ff, 'selftest', return_value=0), \
             patch.object(ff, 'lade_config', return_value=self.cfg), \
             patch.object(ff, 'alle_artikel', return_value=[art]), \
             patch.object(ff, 'geo_reife', return_value=geo), \
             patch.object(ff, 'faelligkeit', return_value=due), \
             patch.object(ff, 'budget_fuer_lauf', return_value=(1, {'quelle': 'test'})), \
             patch.object(ff, '_kapazitaet_nachrechnen', return_value={}), \
             patch.object(ff, 'recherchiere', return_value=dossier), \
             patch.object(ff, 'claude_fachpruefung', return_value=([], [], 'Fehler: Ausfall')), \
             patch.object(ff, 'artikel_anwenden') as apply, \
             patch.object(ff, 'dossier_schreiben'), patch.object(ff, 'report_schreiben'), \
             patch.object(ff, 'QUEUE_PFAD', str(Path(tmp) / 'queue.json')), \
             patch.object(ff, 'HISTORIE_PFAD', str(Path(tmp) / 'history.jsonl')):
            self.assertEqual(ff.main(), 4)
            apply.assert_not_called()
            queue = json.loads(Path(ff.QUEUE_PFAD).read_text(encoding='utf-8'))
            self.assertEqual([item['slug'] for item in queue['offen']], ['test'])
            self.assertEqual(queue['laeufe'][0]['fachpruefung'], 'Fehler: Ausfall')

    def test_findings_survive_a_later_empty_review(self):
        art = {"slug": "test", "titel": "Test", "beschreibung": "", "body": "Preis.",
               "faktencheck": None, "fm": "title: Test\n", "pfad": "test/index.md"}
        geo = {"prozent": 0, "offen": []}
        due = {"faellig": True, "prio": 0, "grund": "neu", "frist": None, "restlaufzeit": None}
        dossier = dict(self.dossier, fehler=[], begriffe=[], kanaele=[], erzeugt="now")
        finding = {"typ": "praezision", "text": "Preis ohne Beleg", "beleg": ""}
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(ff.sys, "argv", ["faktenfrische.py", "--apply"]), \
             patch.object(ff, "selftest", return_value=0), \
             patch.object(ff, "lade_config", return_value=self.cfg), \
             patch.object(ff, "alle_artikel", return_value=[dict(art)]), \
             patch.object(ff, "geo_reife", return_value=geo), \
             patch.object(ff, "faelligkeit", return_value=due), \
             patch.object(ff, "budget_fuer_lauf", return_value=(1, {"quelle": "test"})), \
             patch.object(ff, "_kapazitaet_nachrechnen", return_value={}), \
             patch.object(ff, "recherchiere", return_value=dossier), \
             patch.object(ff, "claude_fachpruefung", side_effect=[
                 ([finding], [self.dossier["treffer"][0]], "geprüft (test)"),
                 ([], [], "geprüft (test)")]), \
             patch.object(ff, "artikel_anwenden", return_value=[]) as apply, \
             patch.object(ff, "dossier_schreiben"), patch.object(ff, "report_schreiben"), \
             patch.object(ff.ledger, "entscheidungen_laden", return_value={}), \
             patch.object(ff, "QUEUE_PFAD", str(Path(tmp) / "queue.json")), \
             patch.object(ff, "HISTORIE_PFAD", str(Path(tmp) / "history.jsonl")):
            self.assertEqual(ff.main(), 0)
            first = json.loads(Path(ff.QUEUE_PFAD).read_text(encoding="utf-8"))
            self.assertEqual(len(first["fachbefunde"]), 1)
            self.assertEqual(ff.main(), 0)
            second = json.loads(Path(ff.QUEUE_PFAD).read_text(encoding="utf-8"))
            self.assertEqual(second["laeufe"][0]["befunde"], [])
            self.assertEqual(second["fachbefunde"], first["fachbefunde"])
            self.assertEqual(second["uebersicht"]["befunde"], 1)
            self.assertEqual(apply.call_args_list[0].args[1], [])

    def test_broken_ledger_stops_before_article_writes(self):
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(ff.sys, "argv", ["faktenfrische.py", "--apply"]), \
             patch.object(ff, "selftest", return_value=0), \
             patch.object(ff, "lade_config", return_value=self.cfg), \
             patch.object(ff, "alle_artikel") as inventory, \
             patch.object(ff, "QUEUE_PFAD", str(Path(tmp) / "queue.json")):
            Path(ff.QUEUE_PFAD).write_text("{kaputt", encoding="utf-8")
            self.assertEqual(ff.main(), 2)
            inventory.assert_not_called()

    def test_feed_dates_are_real_dates(self):
        self.assertEqual(ff.datum_aus_feed('2026-02-30'), '')
        self.assertEqual(ff.datum_aus_feed('31 Feb 2026'), '')
        self.assertEqual(ff.datum_aus_feed('Fri, 26 Sep 2026 08:00'), '2026-09-26')

    def test_stale_article_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'index.md'
            path.write_text('---\ntitle: Test\n---\nOriginal\n', encoding='utf-8')
            art = ff.lade_artikel(str(path))
            path.write_text('---\ntitle: Test\n---\nGeändert\n', encoding='utf-8')
            result = ff.artikel_anwenden(art, [], '2026-10-30', False)
            self.assertIn('seit dem Einlesen verändert', result[0])
            self.assertIn('Geändert', path.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
