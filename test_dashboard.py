import json
import tempfile
import threading
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from http.server import HTTPServer, ThreadingHTTPServer

from server import Dashboard, make_handler
from music_search import MusicSearch, CatalogUnavailable, apple_url
import io
from urllib.error import URLError


class MusicSearchTests(unittest.TestCase):
    def test_results_and_cache(self):
        source = {'results': [
            {'kind': 'song', 'trackId': 1, 'trackName': 'Test Song', 'artistName': 'Artist',
             'trackViewUrl': 'https://music.apple.com/us/album/test/1',
             'previewUrl': 'https://audio-ssl.itunes.apple.com/test.m4a',
             'artworkUrl100': 'https://is1-ssl.mzstatic.com/test.jpg'},
            {'kind': 'song', 'trackId': 2, 'trackViewUrl': 'https://itunes.apple.com/us/test'},
            {'kind': 'song', 'trackViewUrl': 'javascript:alert(1)'},
            {'kind': 'music-video'}]}
        client = MusicSearch()
        with patch('music_search.urlopen', return_value=io.BytesIO(json.dumps(source).encode())) as fetch:
            data = client.search('Test Song', 'AE')
            self.assertEqual(len(data['results']), 2)
            self.assertTrue(data['results'][0]['audio'].endswith('.m4a'))
            self.assertEqual(data['results'][1]['audio'], '')
            self.assertIs(client.search('  test  song ', 'AE'), data)
            self.assertEqual(fetch.call_count, 1)
            self.assertIn('country=AE', fetch.call_args.args[0].full_url)

    def test_validation_errors_limits_and_bad_urls(self):
        client = MusicSearch()
        for term in ('', 'a', 'x' * 101):
            with self.assertRaises(ValueError):
                client.search(term)
        with self.assertRaises(ValueError):
            client.search('Song', 'XX')
        with patch('music_search.urlopen', side_effect=URLError('offline')):
            with self.assertRaises(CatalogUnavailable):
                client.search('Song')
        client.calls = [__import__('time').monotonic()] * 18
        with self.assertRaises(CatalogUnavailable):
            client.search('Another song')
        self.assertEqual(apple_url('https://audio.itunes.apple.com.evil.com/a'), '')
        self.assertEqual(apple_url('http://audio.itunes.apple.com/a'), '')
        self.assertEqual(apple_url('https://evil.com/a', store=True), '')

    def test_empty_and_malformed_responses(self):
        with patch('music_search.urlopen', return_value=io.BytesIO(b'{"results":[]}')):
            self.assertEqual(MusicSearch().search('Nothing')['results'], [])
        with patch('music_search.urlopen', return_value=io.BytesIO(b'not JSON')):
            with self.assertRaises(CatalogUnavailable):
                MusicSearch().search('Something')


class DashboardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'songs.jsonl'
        self.app = Dashboard(self.path)

    def tearDown(self):
        self.temp.cleanup()

    def test_assessment_sequence_and_reverse(self):
        self.app.action(dict(action='insert', key='Sunrise', title='Skyline', duration=200))
        self.app.action(dict(action='insert', key='Marina Lights', title='Night Drive', duration=195))
        self.assertEqual(' / '.join(n.title for n in self.app.nodes()), 'Sunrise / Skyline / Desert Rain / Marina Lights / Night Drive')
        for title in ('Sunrise', 'Desert Rain', 'Night Drive'):
            self.app.action(dict(action='remove', title=title))
        with self.assertRaises(ValueError):
            self.app.action(dict(action='remove', title='Unknown'))
        self.assertEqual(' / '.join(n.title for n in self.app.nodes(True)), 'Marina Lights / Skyline')
        self.app.current = self.app.playlist.tail
        self.app.action(dict(action='next'))
        self.assertEqual(self.app.current.title, 'Skyline')

    def test_persistence_empty_and_current_removal(self):
        self.app.current = self.app.playlist.head
        self.app.action(dict(action='remove', title='Sunrise'))
        self.assertEqual(self.app.current.title, 'Desert Rain')
        self.app.action(dict(action='remove', title='Desert Rain'))
        self.app.action(dict(action='remove', title='Marina Lights'))
        self.assertIsNone(self.app.current)
        self.assertIsNone(self.app.playlist.head)
        self.assertIsNone(self.app.playlist.tail)
        restored = Dashboard(self.path)
        self.assertEqual(restored.state()['songs'], [])
        restored.action(dict(action='next'))
        restored.action(dict(action='previous'))
        restored.action(dict(action='add', title='New', duration=20))
        restored.action(dict(action='next'))
        restored.action(dict(action='previous'))
        self.assertEqual(restored.current.title, 'New')
        self.assertEqual(Dashboard(self.path).playlist.head.title, 'New')

    def test_invalid_input_and_duplicates(self):
        for duration in (0, -1, 2.5, True, '10', 86401):
            with self.assertRaises(ValueError):
                self.app.action(dict(action='add', title='New', duration=duration))
        for title in ('', ' ', 'x' * 31, 7):
            with self.assertRaises(ValueError):
                self.app.action(dict(action='add', title=title, duration=100))
        with self.assertRaises(ValueError):
            self.app.action(dict(action='insert', key='Missing', title='New', duration=100))
        first = self.app.playlist.head
        self.app.action(dict(action='add', title='Sunrise', duration=100))
        second = self.app.playlist.tail
        self.app.current = second
        self.app.action(dict(action='remove', title='Sunrise'))
        self.assertIs(self.app.current, second)
        self.assertIsNone(first.next)

    def test_http_routes_and_validation(self):
        server = HTTPServer(('127.0.0.1', 0), make_handler(self.app))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            for route in ('/', '/app.js', '/discover.js', '/itunes-badge.svg', '/style.css', '/api/state', '/api/state?backward=1'):
                with urlopen(base + route) as response:
                    self.assertEqual(response.status, 200)
                    self.assertTrue(response.read())
            with patch('server.MusicSearch.search', return_value={'results': [], 'country': 'US'}):
                with urlopen(base + '/api/search?q=test') as response:
                    self.assertEqual(json.load(response)['results'], [])
            with urlopen(base + '/style.css') as response:
                self.assertIn('https://*.itunes.apple.com', response.headers['Content-Security-Policy'])
            with self.assertRaises(HTTPError) as caught:
                urlopen(base + '/api/search?q=x')
            self.assertEqual(caught.exception.code, 400)
            request = Request(base + '/api/action', data=json.dumps(dict(action='add', title='<script>test</script>', duration=20)).encode(), headers={'Content-Type': 'application/json'})
            with urlopen(request) as response:
                self.assertEqual(response.status, 200)
            for route in ('/../server.py', '/songs.jsonl'):
                with self.assertRaises(HTTPError) as caught:
                    urlopen(base + route)
                self.assertEqual(caught.exception.code, 404)
            bad = Request(base + '/api/action', data=b'{}', headers={'Content-Type': 'application/json', 'Origin': 'http://example.com'})
            with self.assertRaises(HTTPError) as caught:
                urlopen(bad)
            self.assertEqual(caught.exception.code, 403)
            bad = Request(base + '/api/action', data=b'not json', headers={'Content-Type': 'application/json'})
            with self.assertRaises(HTTPError) as caught:
                urlopen(bad)
            self.assertEqual(caught.exception.code, 400)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_render_hostname_https_and_health(self):
        with patch.dict('os.environ', {'RENDER': 'true', 'RENDER_EXTERNAL_HOSTNAME': 'melody-test.onrender.com'}):
            handler = make_handler(self.app)
        server = ThreadingHTTPServer(('127.0.0.1', 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            headers = {'Host': 'melody-test.onrender.com', 'Origin': 'https://melody-test.onrender.com'}
            with urlopen(Request(base + '/api/state', headers=headers)) as response:
                state = json.load(response)
                self.assertTrue(state['hosted'])
                self.assertEqual(len(state['songs']), 3)
            with urlopen(Request(base + '/healthz', headers={'Host': 'internal-check'})) as response:
                self.assertEqual(json.load(response)['status'], 'ok')
            headers['Origin'] = 'https://another-site.com'
            with self.assertRaises(HTTPError) as caught:
                urlopen(Request(base + '/api/action', data=b'{"action":"next"}',
                                headers={**headers, 'Content-Type': 'application/json'}))
            self.assertEqual(caught.exception.code, 403)

            def add(index):
                payload = json.dumps(dict(action='add', title=f'Concurrent {index}', duration=10)).encode()
                with urlopen(Request(base + '/api/action', data=payload,
                                     headers={'Host': 'melody-test.onrender.com',
                                              'Origin': 'https://melody-test.onrender.com',
                                              'Content-Type': 'application/json'})) as response:
                    return response.status

            with ThreadPoolExecutor(max_workers=4) as executor:
                self.assertTrue(all(code == 200 for code in executor.map(add, range(12))))
            self.assertEqual(len(Dashboard(self.path).state()['songs']), 15)
            node = self.app.playlist.head
            previous = None
            while node:
                self.assertIs(node.prev, previous)
                previous = node
                node = node.next
            self.assertIs(previous, self.app.playlist.tail)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_new_data_directory(self):
        target = Path(self.temp.name) / 'mounted' / 'data' / 'songs.jsonl'
        app = Dashboard(target)
        self.assertTrue(target.is_file())
        self.assertEqual(app.playlist.head.title, 'Sunrise')


if __name__ == '__main__':
    unittest.main()
