import json
from pathlib import Path
import tempfile
import time
import unittest
from urllib.parse import urlencode
from fantasy_manager.core import OAuth, UserError, resource, xml_data, save_private

CONFIG = {'YAHOO_CLIENT_ID': 'test-id', 'YAHOO_CLIENT_SECRET': 'test-secret',
          'YAHOO_REDIRECT_URI': 'https://localhost:8765/callback'}

class FakeTransport:
    def __init__(self, response):
        self.response = response
        self.calls = []
    def request(self, *args):
        self.calls.append(args)
        return json.dumps(self.response).encode()

class ClientTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'tokens.json'
        self.http = FakeTransport({'access_token':'access', 'refresh_token':'refresh', 'expires_in':3600})
        self.oauth = OAuth(CONFIG, self.http, self.path)

    def test_login_and_private_storage(self):
        url, state = self.oauth.start()
        self.assertIn('response_type=code', url)
        self.oauth.finish(CONFIG['YAHOO_REDIRECT_URI'] + '?' + urlencode({'code':'one-use', 'state':state}), state)
        self.assertEqual(self.oauth.access_token(), 'access')
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(len(self.http.calls), 1)

    def test_state_and_destination_rejected_before_exchange(self):
        for callback in ('https://localhost:8765/callback?code=x&state=wrong',
                         'https://evil.example/callback?code=x&state=expected',
                         'https://localhost:8765/callback?code=x&state=expected&state=duplicate'):
            with self.assertRaises(UserError):
                self.oauth.finish(callback, 'expected')
        self.assertFalse(self.http.calls)

    def test_refresh_preserves_old_refresh_token(self):
        save_private(self.path, {'access_token':'old', 'refresh_token':'keep', 'expires_at':0})
        self.http.response = {'access_token':'new', 'expires_in':3600}
        self.assertEqual(self.oauth.access_token(), 'new')
        self.assertEqual(json.loads(self.path.read_text())['refresh_token'], 'keep')
        self.assertIn(b'grant_type=refresh_token', self.http.calls[0][2])

    def test_refresh_rotation(self):
        save_private(self.path, {'access_token':'old', 'refresh_token':'old-refresh', 'expires_at':0})
        self.oauth.access_token()
        self.assertEqual(json.loads(self.path.read_text())['refresh_token'], 'refresh')

    def test_invalid_response_does_not_overwrite_token(self):
        save_private(self.path, {'access_token':'old', 'refresh_token':'keep', 'expires_at':0})
        before = self.path.read_bytes()
        self.http.response = {'error':'invalid_grant'}
        with self.assertRaises(UserError): self.oauth.access_token()
        self.assertEqual(self.path.read_bytes(), before)

    def test_xml_repeated_namespaced_elements(self):
        parsed = xml_data(b'<fantasy_content xmlns="urn:yahoo"><players count="2"><player><name>A</name></player><player><name>B</name></player></players></fantasy_content>')
        self.assertEqual(parsed['fantasy_content']['players']['player'], [{'name':'A'}, {'name':'B'}])
        self.assertEqual(parsed['fantasy_content']['players']['@count'], '2')

    def test_invalid_xml(self):
        with self.assertRaises(UserError): xml_data(b'<broken>')

    def test_routes_and_input_validation(self):
        self.assertEqual(resource('leagues', season=2026), 'users;use_login=1/games;game_codes=nfl;seasons=2026/leagues')
        self.assertEqual(resource('roster', '461.l.123.t.2', 4), 'team/461.l.123.t.2/roster;week=4')
        self.assertEqual(resource('matchups', '461.l.123', 4), 'league/461.l.123/scoreboard;week=4')
        for key in ('../secret', 'https://evil.example', '461.l.1/players'):
            with self.assertRaises(UserError): resource('teams', key)
        with self.assertRaises(UserError): resource('roster', '461.l.123.t.2', 19)

if __name__ == '__main__': unittest.main()
