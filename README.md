# Playlist Bridge

Playlist Bridge is a local, resumable app for moving an owned public Spotify playlist to YouTube Music. It is implemented through the matching, review, recovery, destination, reporting, and browser flows; the final controlled small-playlist acceptance remains a manual gate before a large transfer.

## What it does

- Spotify Authorization Code + PKCE sign-in for the account that owns the source playlist.
- Public playlist inspection and frozen, ordered source import, including intentional duplicates.
- Explainable YouTube Music matching with automatic acceptance for strong matches and a review queue for uncertain results.
- New private/public destinations or append-only writes to an owned playlist.
- Resumable jobs, prefix reconciliation after uncertain writes, history, and CSV/JSON reports.

YouTube Music uses the unofficial `ytmusicapi` library. Google or YouTube Music can change that private interface without notice; the connector is isolated for replacement.

## Quick start

Prerequisites: Python 3.12+, Node.js 22+, and provider OAuth clients configured locally. See [setup.md](docs/setup.md).

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -e "backend[dev]"
npm --prefix frontend install
npm run dev
```

Open the local frontend at `http://127.0.0.1:5173`. Runtime secrets and SQLite data live in the operating-system application-data directory, never in this repository or browser storage.

Run checks with `npm run verify`. The full architecture is documented in [architecture.md](docs/architecture.md), and the small controlled acceptance procedure is in [test-playlist.md](docs/test-playlist.md).

## Scope and safety

Version one is single-user and local. Hosted accounts, ongoing synchronization, reverse transfers, and private Spotify sources are out of scope. Do not begin a 2,500-track transfer until the controlled acceptance playlist passes.

See [SECURITY.md](SECURITY.md), [CONTRIBUTING.md](CONTRIBUTING.md), and the approved [design](docs/superpowers/specs/2026-09-08-spotify-to-youtube-music-design.md).

This project is not affiliated with Spotify, Google, YouTube, or YouTube Music.
