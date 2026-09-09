# Playlist Bridge

Playlist Bridge is a planned local web application for transferring an owned public Spotify playlist to YouTube Music. It is designed for very large playlists, explainable song matching, manual review of uncertain results, exact ordering, intentional duplicates, and interruption-safe resume.

> **Project status:** Product design and implementation planning are complete. Application code has not started.

## Planned workflow

1. Connect the Spotify account that owns the public source playlist.
2. Paste the Spotify playlist URL.
3. Match tracks against the YouTube Music catalog.
4. Review only uncertain or missing matches.
5. Create a new public or private YouTube Music playlist, or append to an existing owned playlist.
6. Resume safely after interruption and export a complete result report.

## Architecture

- React and TypeScript browser interface
- FastAPI Python backend bound to the local computer
- SQLite job, review, and recovery state
- Official Spotify Web API with Authorization Code and PKCE
- Isolated, version-pinned ytmusicapi integration for YouTube Music

ytmusicapi is unofficial and emulates the YouTube Music web client. Google may change that private interface without notice. The connector is intentionally isolated so compatibility updates do not affect the rest of the application.

## Privacy and repository safety

Playlist Bridge is local-only in its first version. OAuth material, cookies, tokens, runtime databases, and transfer history must remain in the operating system's per-user application-data directory. They must never be committed, logged, placed in reports, or returned to the browser as raw values.

This repository intentionally ignores common credential and runtime filenames. Before every public release, tracked files will be scanned for secrets and generated data. If a credential is ever committed, revoke it immediately; deleting it from a later commit is not sufficient.

## Documentation

- [Approved product design](docs/superpowers/specs/2026-09-08-spotify-to-youtube-music-design.md)
- [Implementation plan](docs/superpowers/plans/2026-09-09-playlist-transfer-app.md)
- [Documentation index](docs/README.md)
- [Security policy](SECURITY.md)
- [Contributing guide](CONTRIBUTING.md)

## Development

Implementation will follow the checked, task-by-task plan. Each task starts with a failing test, ends with its focused and affected suites passing, receives a secret scan and diff review, and lands as a separate commit.

The first executable development instructions will be added with Task 1. Until then, the repository is a transparent planning artifact.

## Scope

Version one is single-user and local. Hosted accounts, ongoing synchronization, private Spotify sources, reverse transfers, and mobile or desktop-native clients require separate designs.

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by Spotify, Google, YouTube, or YouTube Music. Spotify and YouTube Music are trademarks of their respective owners.

## License

[MIT](LICENSE)
