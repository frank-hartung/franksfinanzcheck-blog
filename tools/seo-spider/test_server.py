import json
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from http.server import ThreadingHTTPServer

sys.path.insert(0, str(Path(__file__).parent))
import server as spider_server


class LocalServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = ThreadingHTTPServer(('127.0.0.1', 0), spider_server.Handler)
        cls.thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.httpd.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.thread.join(timeout=2)

    def setUp(self):
        spider_server.STOP.clear()
        with spider_server.LOCK:
            spider_server.STATE.update(running=False, done=False, pages=[], links=[], error='', summary={})

    def test_local_ui_has_no_external_runtime_dependency(self):
        with urllib.request.urlopen(self.base + '/', timeout=2) as response:
            html = response.read().decode()
            self.assertEqual(response.status, 200)
            self.assertIn('check-external', html)
            self.assertIn('export-links.csv', html)
            self.assertNotIn('fonts.googleapis.com', html)

    def test_cross_origin_posts_are_blocked(self):
        request = urllib.request.Request(self.base + '/api/start', data=b'{"url":"https://example.com/"}', headers={'Origin':'https://attacker.invalid','Content-Type':'application/json'}, method='POST')
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=2)
        self.assertEqual(caught.exception.code, 403)

    def test_private_targets_are_rejected_before_any_network_fetch(self):
        request = urllib.request.Request(self.base + '/api/start', data=json.dumps({'url':'http://127.0.0.1/'}).encode(), headers={'Content-Type':'application/json'}, method='POST')
        with urllib.request.urlopen(request, timeout=2) as response:
            self.assertEqual(response.status, 202)
        for _ in range(50):
            with urllib.request.urlopen(self.base + '/api/state', timeout=2) as response:
                state = json.load(response)
            if state['done']:
                break
            time.sleep(.02)
        self.assertTrue(state['done'])
        self.assertIn('private', state['error'].lower())

    def test_exports_are_dispositioned_as_downloads(self):
        with urllib.request.urlopen(self.base + '/api/export-links.csv', timeout=2) as response:
            self.assertEqual(response.headers['Content-Type'], 'text/csv; charset=utf-8')
            self.assertIn('attachment', response.headers['Content-Disposition'])


if __name__ == '__main__':
    unittest.main()
