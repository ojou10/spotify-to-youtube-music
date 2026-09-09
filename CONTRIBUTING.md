# Contributing

Thank you for helping build Playlist Bridge.

## Before implementation

Read the approved [design](docs/superpowers/specs/2026-09-08-spotify-to-youtube-music-design.md) and [implementation plan](docs/superpowers/plans/2026-09-09-playlist-transfer-app.md). Changes that expand product scope or alter provider boundaries should update the design before code is changed.

## Development rules

- Keep files focused and provider integrations isolated.
- Add a failing test before changing behavior.
- Preserve source order and intentional duplicate tracks.
- Keep remote work serial and resumable.
- Use stable, redacted application errors.
- Do not add hosted or multi-user behavior to version one.
- Keep commits focused on one reviewed plan task.

## Sensitive data

Never commit or attach:

- environment files with values;
- OAuth documents, cookies, tokens, codes, or authorization headers;
- Spotify or Google client secrets;
- runtime SQLite databases;
- real playlist exports, recorded provider payloads, or personal identifiers;
- private keys or production logs.

Use synthetic fixtures. Before committing, inspect tracked files and run the repository secret check once it is introduced by the implementation plan.

## Pull requests

Explain which plan task or approved design change the pull request implements. Include the failing test that drove the change, the commands used to verify it, recovery or disclosure risks considered, and screenshots only when they contain synthetic data.
