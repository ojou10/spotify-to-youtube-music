# Contributing

Keep changes organized, tested, and safe for a public repository. Never commit provider credentials, OAuth JSON, cookies, SQLite databases, build output, or real playlist payloads.

Run `npm run verify` before opening a pull request. Backend changes should include focused pytest coverage and frontend changes should include component coverage where behavior changes. Provider integration tests must remain read-only and opt-in. Keep `ytmusicapi` imports inside the YouTube connector boundary.
