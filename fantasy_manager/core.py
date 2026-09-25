"""Yahoo OAuth and Fantasy API client, using only the Python standard library."""
import base64
import json
import os
from pathlib import Path
import re
import secrets
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, parse_qs
from urllib.request import Request, build_opener, HTTPRedirectHandler
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
AUTH_URL = 'https://api.login.yahoo.com/oauth2/request_auth'
TOKEN_URL = 'https://api.login.yahoo.com/oauth2/get_token'
API_URL = 'https://fantasysports.yahooapis.com/fantasy/v2/'

class UserError(Exception):
    """An actionable error safe to show without revealing credentials."""

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

class Transport:
    def request(self, url, headers=None, data=None):
        try:
            with build_opener(NoRedirect).open(Request(url, data=data, headers=headers or {}), timeout=30) as response:
                return response.read()
        except HTTPError as error:
            messages = {400: 'Yahoo rejected the request. Check the redirect URI, credentials, or sign in again.',
                        401: 'Yahoo authentication failed. Run auth again.',
                        403: 'Yahoo denied access. Confirm API approval and Fantasy Sports permissions.',
                        404: 'Yahoo resource not found. Check the league or team key.',
                        429: 'Yahoo rate limit reached. Wait before trying again.'}
            raise UserError(messages.get(error.code, 'Yahoo request failed (HTTP %s). Try again later.' % error.code)) from None
        except (URLError, TimeoutError, OSError):
            raise UserError('Could not reach Yahoo. Check your connection and try again.') from None


def settings():
    config = {}
    path = ROOT / '.env'
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            key, sep, value = line.partition('=')
            if not sep:
                raise UserError('Invalid .env line: expected KEY=value.')
            config[key.strip()] = value.strip().strip('\"\'')
    for key in ('YAHOO_CLIENT_ID', 'YAHOO_CLIENT_SECRET', 'YAHOO_REDIRECT_URI'):
        if key in os.environ:
            config[key] = os.environ[key]
        if not config.get(key) or config[key].startswith('REPLACE_'):
            raise UserError('Set %s in the local .env file first. See .env.example.' % key)
    uri = urlsplit(config['YAHOO_REDIRECT_URI'])
    if uri.hostname not in ('localhost', '127.0.0.1') or uri.scheme not in ('http', 'https') or uri.query or uri.fragment or uri.username:
        raise UserError('Use a Yahoo-registered loopback redirect URI without query or fragment, such as https://localhost:8765/callback.')
    return config


def save_private(path, data):
    path = Path(path)
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    try:
        with os.fdopen(fd, 'w') as handle:
            json.dump(data, handle, indent=2)
            handle.write('\n')
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class OAuth:
    def __init__(self, config, transport=None, token_path=None):
        self.config = config
        self.transport = transport or Transport()
        self.token_path = Path(token_path) if token_path else ROOT / 'tokens/yahoo.json'

    def start(self):
        state = secrets.token_urlsafe(32)
        return AUTH_URL + '?' + urlencode({'client_id': self.config['YAHOO_CLIENT_ID'],
            'redirect_uri': self.config['YAHOO_REDIRECT_URI'], 'response_type': 'code', 'state': state}), state

    def finish(self, callback, state):
        actual = urlsplit(callback.strip())
        expected = urlsplit(self.config['YAHOO_REDIRECT_URI'])
        if (actual.scheme, actual.netloc, actual.path) != (expected.scheme, expected.netloc, expected.path) or actual.fragment:
            raise UserError('Callback URL does not match the configured redirect URI.')
        values = parse_qs(actual.query)
        if len(values.get('state', [])) != 1 or not secrets.compare_digest(values['state'][0], state):
            raise UserError('Sign-in state mismatch. Start auth again; do not reuse an earlier callback.')
        if 'error' in values:
            raise UserError('Yahoo authorization was declined or failed. Start auth again.')
        if len(values.get('code', [])) != 1:
            raise UserError('Callback URL must contain exactly one authorization code.')
        return self.exchange({'grant_type': 'authorization_code', 'code': values['code'][0],
                              'redirect_uri': self.config['YAHOO_REDIRECT_URI']})

    def exchange(self, fields, previous=None):
        basic = base64.b64encode(('%s:%s' % (self.config['YAHOO_CLIENT_ID'], self.config['YAHOO_CLIENT_SECRET'])).encode()).decode()
        raw = self.transport.request(TOKEN_URL, {'Authorization': 'Basic ' + basic,
            'Content-Type': 'application/x-www-form-urlencoded'}, urlencode(fields).encode())
        try:
            result = json.loads(raw)
            if not isinstance(result.get('access_token'), str) or not result['access_token']:
                raise ValueError()
            ttl = float(result['expires_in'])
            if not 0 < ttl < 365 * 86400:
                raise ValueError()
            refresh = result.get('refresh_token') or (previous or {}).get('refresh_token')
            if not isinstance(refresh, str) or not refresh:
                raise ValueError()
            token = {'access_token': result['access_token'], 'refresh_token': refresh, 'expires_at': time.time() + ttl}
        except (ValueError, KeyError, TypeError, AttributeError):
            raise UserError('Yahoo returned an invalid token response. Run auth again.') from None
        save_private(self.token_path, token)
        return token

    def access_token(self):
        try:
            token = json.loads(self.token_path.read_text())
            if not isinstance(token['access_token'], str) or not isinstance(token['refresh_token'], str):
                raise ValueError()
            expiry = float(token['expires_at'])
        except (OSError, ValueError, KeyError, TypeError):
            raise UserError('No valid saved login. Run python3 -m fantasy_manager auth.') from None
        if expiry <= time.time() + 60:
            token = self.exchange({'grant_type': 'refresh_token', 'refresh_token': token['refresh_token']}, token)
        return token['access_token']


def xml_data(raw):
    """Preserve Yahoo's nested fields, repeated elements, and attributes as JSON."""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        raise UserError('Yahoo returned invalid XML.') from None
    def local(tag):
        return tag.rsplit('}', 1)[-1]
    def convert(element):
        result = {'@' + local(k): v for k, v in element.attrib.items()}
        for child in element:
            key = local(child.tag)
            value = convert(child)
            if key in result:
                if not isinstance(result[key], list):
                    result[key] = [result[key]]
                result[key].append(value)
            else:
                result[key] = value
        text = (element.text or '').strip()
        if not result:
            return text
        if text:
            result['#text'] = text
        return result
    return {local(root.tag): convert(root)}


def resource(command, key=None, week=None, season=None):
    if command == 'leagues':
        path = 'users;use_login=1/games;game_codes=nfl'
        if season:
            path += ';seasons=%s' % season
        return path + '/leagues'
    pattern = r'\d+\.l\.\d+' + (r'\.t\.\d+' if command == 'roster' else '')
    if not key or not re.fullmatch(pattern, key):
        raise UserError('Use the full Yahoo %s key returned by the API.' % ('team' if command == 'roster' else 'league'))
    if week is not None and not 1 <= week <= 18:
        raise UserError('Week must be between 1 and 18.')
    if command == 'roster':
        path = 'team/%s/roster' % key
    else:
        path = 'league/%s/%s' % (key, {'teams': 'teams', 'standings': 'standings', 'matchups': 'scoreboard'}[command])
    if week is not None:
        path += ';week=%s' % week
    return path


def fetch(oauth, path):
    raw = oauth.transport.request(API_URL + path, {'Authorization': 'Bearer ' + oauth.access_token(), 'Accept': 'application/xml'})
    return xml_data(raw)
