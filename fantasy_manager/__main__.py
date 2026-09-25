"""Run with python3 -m fantasy_manager."""
import argparse
import getpass
import json
import sys
import webbrowser
from .core import ROOT, OAuth, UserError, fetch, resource, save_private, settings


def main():
    parser = argparse.ArgumentParser(description='Personal read-only Yahoo Fantasy Football manager')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('demo', help='Show fictional sample roster; no credentials or network needed')
    sub.add_parser('auth', help='Authorize Yahoo access and save tokens locally')
    for name in ('leagues', 'teams', 'roster', 'standings', 'matchups'):
        p = sub.add_parser(name, help='Fetch your ' + name)
        if name != 'leagues':
            p.add_argument('key', help='Full Yahoo team key for roster; league key otherwise')
        else:
            p.add_argument('--season', type=int, help='Season year; omit to query available NFL games')
        if name in ('roster', 'matchups'):
            p.add_argument('--week', type=int, help='NFL week 1–18; omit for current week')
        p.add_argument('--save', action='store_true', help='Also save a private snapshot under data/')
    args = parser.parse_args()
    try:
        if args.command == 'demo':
            print(json.dumps({'sample_data': True, 'team': 'Example Team (fictional)', 'week': 3,
                'roster': [{'name': 'Sample Quarterback', 'position': 'QB', 'status': 'Healthy'},
                           {'name': 'Sample Running Back', 'position': 'RB', 'status': 'Questionable'}]}, indent=2))
            return 0
        oauth = OAuth(settings())
        if args.command == 'auth':
            url, state = oauth.start()
            print('Opening Yahoo sign-in. If it does not open, visit:\n' + url)
            webbrowser.open(url)
            print('\nAfter consenting, Yahoo redirects to your registered localhost URL.\n'
                  'No callback server is running: a connection error is expected.\n'
                  'Copy the complete URL from the address bar and paste below.\n'
                  'Do not bypass browser certificate warnings. Do not share the URL.\n')
            oauth.finish(getpass.getpass('Callback URL (hidden): '), state)
            print('Yahoo login saved locally in tokens/yahoo.json.')
            return 0
        path = resource(args.command, getattr(args, 'key', None), getattr(args, 'week', None), getattr(args, 'season', None))
        data = fetch(oauth, path)
        print(json.dumps(data, indent=2))
        if args.save:
            save_private(ROOT / 'data' / (args.command + '.json'), data)
            print('Snapshot saved to data/%s.json (replaces the previous snapshot).' % args.command, file=sys.stderr)
        return 0
    except (UserError, OSError) as error:
        message = str(error) if isinstance(error, UserError) else 'Could not read or write local files. Check file permissions.'
        print('Error: ' + message, file=sys.stderr)
        return 1
    except (KeyboardInterrupt, EOFError):
        print('\nCancelled.', file=sys.stderr)
        return 130

if __name__ == '__main__':
    sys.exit(main())
