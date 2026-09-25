# My Fantasy Football Manager

A personal, non-commercial project for reviewing my Yahoo Fantasy Football team. The local Yahoo API integration is not implemented yet.

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
python3 -m http.server 8000 --bind 127.0.0.1
```

Open http://127.0.0.1:8000/ and stop the server with Ctrl+C.

## Yahoo application

Use the published website URL for the app website/homepage field once it is live. It is not an OAuth redirect URI; configure authentication separately when implementing the local app.

Suggested project description:

> A personal, non-commercial application running on my own computer to review my Yahoo Fantasy Football roster, league standings, matchups, and player information. The initial scope is read-only analysis to help me make lineup and waiver decisions in Yahoo Fantasy. It will access only data authorized through my Yahoo account, with no public service or resale of data.

## Local development

The repository is cloned at `/Users/straulin/personal_scripts/my_fantasy_football_manager`.

Planned first milestone: Yahoo OAuth authentication and read-only roster retrieval after API access is approved. Store secrets in a local `.env` file and token files in `tokens/`; both are ignored by Git. Never publish secrets or fantasy data. The landing page does not run the local application.
