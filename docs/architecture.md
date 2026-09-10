# Architecture

The React/TypeScript frontend talks to a FastAPI backend over a loopback `/api` boundary. SQLite stores jobs, frozen source positions, candidates, decisions, append batches, and safe events. Provider credentials are stored atomically under the operating-system per-user application-data directory.

Spotify uses the official Web API and PKCE. YouTube Music is isolated behind `YouTubeMusicAuth` and `YouTubeMusicConnector`, backed by `ytmusicapi`. The matching engine has no network or database access: it normalizes metadata, builds deterministic queries, scores candidates, and classifies auto/review/unmatched results.

A single worker owns long-running matching and remote writes. Each destination batch is persisted before sending; after an uncertain outcome, the observed destination tail is compared with the planned prefix before resuming. Reports stream from source-position order.
