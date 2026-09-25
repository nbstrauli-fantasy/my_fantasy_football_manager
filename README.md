# My Fantasy Football Manager

A personal, non-commercial project for reviewing my Yahoo Fantasy Football team. The initial Python command-line client supports OAuth and read-only Yahoo API queries. Live access requires Yahoo approval and configured credentials.

## Project website

Static landing page: `index.html`. No build system or dependencies are required.

Expected URL after GitHub Pages is enabled:
https://nbstrauli-fantasy.github.io/my_fantasy_football_manager/

### Publish with GitHub Pages

1. Push this repository's changes to `main`.
2. Open repository **Settings → Pages**.
3. Under **Build and deployment**, choose **Deploy from a branch**.
4. Choose branch **main** and folder **/ (root)**, then **Save**.
5. Wait for the Pages deployment to finish and verify the site loads.

The repository root is the website publishing source. Keep credentials and personal data out of Git entirely.

### Preview locally

```sh
python3 preview_site.py
```

Open http://127.0.0.1:8000/ and stop the server with Ctrl+C.

## Yahoo application

Use the published website URL for the app website/homepage field once it is live. It is not an OAuth redirect URI; configure authentication separately when implementing the local app.

Suggested project description:

> A personal, non-commercial application running on my own computer to review my Yahoo Fantasy Football roster, league standings, matchups, and player information. The initial scope is read-only analysis to help me make lineup and waiver decisions in Yahoo Fantasy. It will access only data authorized through my Yahoo account, with no public service or resale of data.

## Local development

The repository is cloned at `/Users/straulin/personal_scripts/my_fantasy_football_manager`.

### Requirements and offline start

Python 3.9 or later. No external dependencies or package installation required.

```sh
cd /Users/straulin/personal_scripts/my_fantasy_football_manager
python3 -m fantasy_manager demo
python3 -m fantasy_manager --help
python3 -m unittest discover -s tests -v
```

The demo uses explicitly fictional data and makes no network requests. API commands output nested JSON converted from Yahoo XML; they do not yet provide player rankings or lineup recommendations.

### Configure after approval

1. Confirm that Yahoo has enabled Fantasy Sports read permissions for your developer app.
2. Register a loopback OAuth redirect URI accepted by Yahoo, for example `https://localhost:8765/callback`. This is separate from the public GitHub Pages homepage. Exact redirect acceptance must be confirmed in Yahoo's developer console.
3. Copy the example configuration once and restrict its permissions:

```sh
cp -n .env.example .env
chmod 600 .env
```

4. Edit `.env` locally with your client ID, client secret, and the exact registered redirect URI. Never paste credentials into chat or commit them. Environment variables with the same names override the file.
5. Run `python3 -m fantasy_manager auth`.

The browser opens Yahoo sign-in. After consent, copy the complete redirect URL from the address bar into the terminal's hidden prompt. There is no callback server in this version, so a localhost connection failure is expected. Do not bypass a browser certificate warning; copy the address instead. The callback must match the configured URI and include this login attempt's state and code. A plain code or callback from an earlier attempt is rejected.

This manual loopback flow has not yet been tested with this Yahoo application's live credentials. If Yahoo rejects the redirect URI, resolve the registered URI before continuing; do not use the public website to receive authorization codes.

### Find your team and retrieve data

```sh
python3 -m fantasy_manager leagues --season 2026
python3 -m fantasy_manager teams 461.l.12345
python3 -m fantasy_manager roster 461.l.12345.t.1
python3 -m fantasy_manager roster 461.l.12345.t.1 --week 4 --save
python3 -m fantasy_manager standings 461.l.12345
python3 -m fantasy_manager matchups 461.l.12345 --week 4
```

The keys above are examples, not your league. Copy a `league_key` from the leagues output, then a `team_key` from the teams output. Omitting the season queries the available NFL games for your account; omitting the week uses Yahoo's current week.

### Local data and authentication

- `.env` stores credentials locally and is ignored by Git.
- `tokens/yahoo.json` stores the access and refresh tokens with owner-only file permissions (0600), using atomic replacement. Tokens are refreshed shortly before expiry, including refresh-token rotation.
- `--save` writes an owner-only snapshot to `data/<command>.json`, replacing that command's previous snapshot. Otherwise results only go to the terminal.
- `tokens/`, `credentials/`, and `data/` are ignored by Git. They are not encrypted at rest. Keep your local user account secure.
- Commands only read Fantasy resources. There are no roster changes, trades, waiver submissions, background jobs, or automatic polling.
- Errors avoid printing Yahoo response bodies, secrets, tokens, and authorization codes. A 403 generally means approval or permissions need attention; a 401 requires signing in again. Rate limiting is surfaced rather than retried in a loop.
- To remove the saved local login, delete `tokens/yahoo.json`. Revoke the application's access in Yahoo separately if needed.

The website preview script serves only `index.html`; requests for `.env`, tokens, and other repository files return 404. Do not replace it with a general-purpose directory server once credentials exist.

### Validation and current limits

Offline tests cover OAuth state and redirect checks, private token storage, refresh-token preservation and rotation, invalid responses, XML namespaces/repeated elements, and API path validation. Live OAuth and Fantasy API responses still require verification after approval. The app preserves Yahoo's data structure rather than assuming a specific league scoring system.

Official references:
- https://developer.yahoo.com/oauth2/guide/flows_authcode/
- https://sports.yahoo.com/developer/docs/
