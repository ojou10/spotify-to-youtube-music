# Spotify to YouTube Music Transfer App — Design Specification

**Status:** Approved design  
**Date:** 2026-09-08  
**Last updated:** 2026-09-09
**Initial deployment:** Local, single-user application  
**Potential future deployment:** Downloadable local application and hosted multi-user service

## 1. Summary

Build a local browser application that copies a public Spotify playlist to YouTube Music. The first target playlist contains approximately 2,500 tracks, so the application must be resumable, preserve the source order and intentional duplicates, and provide efficient review of uncertain matches.

The user connects the Spotify account that owns the public playlist and pastes its URL. The application imports a frozen snapshot of its tracks, searches the YouTube Music catalog, automatically accepts strong matches, and asks the user to resolve uncertain or missing matches. It then either creates a new YouTube Music playlist or appends the resolved sequence to an existing playlist.

The application uses Spotify's official Web API for source data and the unofficial `ytmusicapi` library for YouTube Music search and playlist management. The YouTube connector is isolated so it can be repaired or replaced without changing the matching, persistence, or user-interface layers.

## 2. Goals

- Transfer one public Spotify playlist owned by the connected Spotify account at a time to YouTube Music.
- Handle playlists with at least 2,500 source positions.
- Preserve the source position of every supported item and preserve intentional duplicates.
- Automatically accept only high-confidence matches.
- Give the user an efficient way to resolve uncertain and unmatched tracks.
- Create a new destination playlist or append to an existing destination playlist.
- Allow public or private visibility for a new destination, defaulting to private.
- Save all meaningful progress and safely resume after a browser or backend interruption.
- Produce a durable result report and allow JSON and CSV export.
- Keep credentials and authentication data on the local computer.
- Keep the React/FastAPI boundary clean enough that hosted and packaged variants can be designed later.

## 3. Non-goals for Version One

- Multi-user accounts, hosted deployment, cloud queues, or shared storage.
- Reverse transfers from YouTube Music to Spotify.
- Automatic ongoing synchronization after an initial transfer.
- Editing, replacing, or reconciling the pre-existing contents of a destination playlist.
- Removing duplicates from the Spotify source.
- Transferring podcast episodes, local Spotify files, or unavailable Spotify items.
- Supporting private Spotify playlists or playlists the connected Spotify user does not own.
- Guaranteeing uninterrupted compatibility with YouTube Music's private web interface.
- Mobile-native or desktop-native clients.

## 4. Confirmed Product Decisions

- The app is local and single-user for version one.
- The UI is React with TypeScript.
- The backend is Python with FastAPI.
- SQLite is the durable store.
- The Spotify source playlist is public and is supplied by URL.
- The app requires Spotify sign-in and verifies that the connected user owns the source playlist.
- Spotify authentication uses Authorization Code with PKCE so a distributed local client does not embed a Spotify client secret.
- YouTube Music access uses `ytmusicapi` authentication stored locally.
- Strong matches are accepted automatically; uncertain matches require review.
- New destinations may be public or private and default to private.
- Existing destinations are append-only.
- Order and duplicates are preserved exactly among supported, accepted source positions.
- Future distribution and hosting are acknowledged but are not version-one requirements.

## 5. Technology and Repository Shape

Use a small monorepo with independently testable frontend and backend packages:

```text
frontend/                 React, TypeScript, Vite
backend/
  app/
    api/                  FastAPI routes and schemas
    connectors/           Spotify and YouTube Music adapters
    matching/             Normalization, scoring, classification
    transfer/             Job state machine, workers, reconciliation
    persistence/          SQLite models, repositories, migrations
    settings/             Local configuration and credential handling
  tests/
docs/                     Design and operational documentation
```

Runtime data does not live in the repository. It uses a per-user operating-system application-data directory, such as `%LOCALAPPDATA%/PlaylistBridge` on Windows.

The frontend talks only to the backend's JSON API and Server-Sent Events stream. It never calls Spotify or YouTube Music directly and never receives stored secrets.

The backend runs one transfer worker and one active remote-write phase at a time. Matching and review data for multiple jobs may remain stored, but serial remote work keeps rate limiting and recovery understandable for a personal application.

## 6. Components and Boundaries

### 6.1 React frontend

Responsibilities:

- Render setup, source inspection, destination choice, progress, review, transfer, history, and report screens.
- Keep only transient presentation state in the browser.
- Read canonical job and match state from the backend.
- Send explicit review decisions and job commands.
- Consume progress events and fall back to periodic refresh if the event stream disconnects.

Dependencies: the versioned FastAPI contract only.

### 6.2 FastAPI API layer

Responsibilities:

- Validate playlist URLs and request bodies.
- Convert backend domain objects into stable response schemas.
- Enforce legal job transitions.
- Start, pause, resume, and cancel work through the transfer service.
- Stream compact progress events.
- Never perform a complete long-running transfer inside a request handler.

Dependencies: application services and repositories, not connector implementations directly.

### 6.3 Spotify connector

Responsibilities:

- Authenticate the playlist owner through Spotify Authorization Code with PKCE and refresh access tokens locally.
- Parse and validate public Spotify playlist identifiers.
- Verify that the connected Spotify user owns the playlist and that the playlist is public.
- Fetch playlist metadata and every page of playlist items.
- Return normalized source records while preserving original positions.
- Surface unavailable tracks, local files, episodes, and malformed items explicitly.

The connector exposes domain values rather than raw Spotify response objects.

### 6.4 YouTube Music connector

Responsibilities:

- Set up and validate local YouTube Music authentication.
- Search the Songs category and return normalized candidates.
- List user-owned playlists and retrieve destination contents.
- Create playlists with the chosen visibility.
- Append an ordered list of video IDs.
- Translate `ytmusicapi` errors into stable application errors.

All `ytmusicapi` calls live in this connector. The dependency is version-pinned and updated only after connector contract tests pass.

### 6.5 Matching engine

Responsibilities:

- Normalize source and candidate metadata.
- Build a small, deterministic sequence of search queries.
- Deduplicate candidates by YouTube video ID.
- Score candidates using pure functions.
- Classify the best candidate as auto-accepted, review-required, or unmatched.
- Store the score explanation so the UI can explain a decision.

The matching engine has no network or database access.

### 6.6 Transfer engine

Responsibilities:

- Execute the durable job state machine.
- Resume work from stored item-level and batch-level state.
- Apply throttling, retry, pause, cancellation, and conflict rules.
- Reconcile a destination playlist after an uncertain remote-write outcome.
- Emit progress without treating the browser connection as job ownership.

### 6.7 Persistence layer

Responsibilities:

- Store jobs, the frozen Spotify snapshot, candidate matches, user decisions, destination details, append batches, and event history.
- Apply short database transactions around each state transition.
- Provide migrations from the first release onward.

SQLite uses write-ahead logging. Domain services access it through repositories so a hosted version could later use another database without changing connector or matching code.

## 7. Core Data Model

### `transfer_jobs`

- `id`: UUID
- `status`: job state enum
- `source_playlist_id`, `source_url`, `source_name`, `source_owner`
- `source_snapshot_marker`: Spotify snapshot identifier when available
- `source_track_count`, `supported_count`
- `destination_mode`: `create` or `append`
- `destination_playlist_id`, `destination_name`, `destination_visibility`
- `destination_base_length`: length observed immediately before append begins
- `match_cursor`, `write_cursor`
- aggregate counts for accepted, review, unmatched, skipped, transferred, and failed
- timestamps and last safe error summary

### `source_items`

One row per original Spotify playlist position, including duplicates.

- `id`, `job_id`, `source_position`
- Spotify track ID and URL when present
- title, artists, album, duration, ISRC when present
- support status and reason
- match status and selected YouTube video ID
- transfer status and error summary

Uniqueness is `(job_id, source_position)`, not Spotify track ID, because duplicates must remain distinct.

### `match_candidates`

- `id`, `source_item_id`, YouTube video ID
- title, artists, album, duration, result type, thumbnail
- total score, score breakdown, rank, and search query origin

Candidate rows are replaceable until the user makes a decision. A user-selected candidate remains referenced by the source item even if a later search refreshes other candidates.

### `append_batches`

- `id`, `job_id`, zero-based batch index
- planned start and end offsets in the final accepted-item sequence
- ordered video IDs serialized for reconciliation
- state: planned, sending, confirmed, or uncertain
- attempt count, timestamps, and last error

### `job_events`

A bounded operational history of state changes, warnings, retries, pauses, conflicts, and completion. Secrets and full upstream payloads are never recorded.

## 8. Job State Machine

The legal top-level states are:

```text
draft
  -> importing_source
  -> matching
  -> awaiting_review
  -> ready_to_transfer
  -> preparing_destination
  -> transferring
  -> completed
```

Any active state may enter `pausing` and then `paused`. Recoverable errors enter `paused` with a reason and a permitted resume action. A user cancellation enters `cancelled` after the current atomic operation finishes. An unrecoverable invariant failure enters `failed`.

Review can return selected source items to matching without discarding decisions for other items. Transfer cannot begin while any supported item remains undecided; every supported item must be accepted or explicitly skipped.

The backend validates every transition. Reloading or closing the browser does not change a job state.

## 9. Source Import

1. Require an active Spotify user session, parse the Spotify URL, and extract a playlist ID.
2. Fetch playlist metadata, verify that the connected user owns it and that it is public, then display the preview before job creation.
3. On confirmation, create a job and page through every playlist item.
4. Store each item by original source position in short transactions.
5. Classify local files, episodes, unavailable tracks, and malformed entries as unsupported with a visible reason.
6. Freeze the imported source snapshot. Later changes to Spotify do not silently alter the active job.

If import is interrupted, resume at the first missing source position. If Spotify's snapshot marker changes during import, discard only the incomplete snapshot and restart import after notifying the user. Once import completes, later source changes do not affect that job.

## 10. Matching Design

### 10.1 Search strategy

For each supported source item, query YouTube Music's Songs filter in this order until enough distinct candidates exist:

1. Exact title plus all credited artists.
2. Exact title plus primary artist.
3. Title plus primary artist plus album.
4. Simplified title with bracketed version text removed, plus primary artist.

Keep at most the top five distinct candidates per source item. Stop early when a candidate passes the auto-accept rules with a sufficient margin over the runner-up. Requests are serial and use a conservative randomized delay. Temporary failures use exponential backoff with jitter.

### 10.2 Normalization

- Apply Unicode NFKC normalization and case folding.
- Normalize whitespace and punctuation.
- Treat `&`, `and`, and common featuring tokens consistently.
- Separate version markers from the base title.
- Compare artist sets without requiring their displayed order to match.
- Do not remove meaningful qualifiers such as live, acoustic, remix, instrumental, karaoke, sped-up, slowed, or remastered; compare them separately.

### 10.3 Initial scoring model

The deterministic score is clamped to 0–100:

- title similarity: 0–35
- artist similarity: 0–30
- duration similarity: 0–15
- album similarity: 0–10
- Songs result-type confidence: 0–5
- compatible version markers: 0–5

Apply a 25-point penalty when the candidate contains a major version marker absent from the source, or conflicts with a source marker. Apply an 8-point penalty for a remaster-only mismatch. Store all component values and penalties.

Initial classification rules:

- **Auto-accepted:** score at least 86 and at least 8 points above the next candidate. If there is no runner-up, the margin is treated as 100.
- **Review-required:** score at least 65 but below the auto-accept rule, or any top-two margin below 8.
- **Unmatched:** no candidate reaches 65.

Thresholds are backend constants covered by fixture tests. They are not user settings in version one. Calibration may change the constants before release, but it must not change already stored decisions in an active job.

## 11. Review Experience

The review page supports server-side filtering and pagination or virtualized rows. Filters include review-required, unmatched, unsupported, manually resolved, and skipped.

For each unresolved track, the user may:

- accept one of the stored candidates;
- run a custom YouTube Music search;
- paste a YouTube or YouTube Music track URL, which the backend validates;
- skip the source position.

The page shows title, artist, album, duration, version markers, confidence score, and score explanation for both sides. Audio or video preview links open the corresponding YouTube Music item; the app does not stream media itself.

Bulk actions are limited to safe operations, such as accepting all candidates above a displayed score. No bulk action may silently accept unmatched items.

## 12. Destination and Write Semantics

### 12.1 New playlist

The user supplies or accepts the imported playlist name, may edit the description, and chooses public or private visibility. Private is the default. The playlist is created only after review is complete.

### 12.2 Existing playlist

The user selects a playlist owned by the authenticated YouTube Music account. Version one only appends; it never removes, replaces, reorders, or deduplicates existing items. Immediately before writing, the backend records the destination length and verifies that the planned additions are allowed.

### 12.3 Ordered append and recovery

Build the final ordered sequence from accepted source positions, excluding unsupported and explicitly skipped positions. Chunk the sequence into connector-safe batches while preserving order and intentional duplicates.

For every batch:

1. Store the ordered plan and mark it `sending`.
2. Send it through the YouTube Music connector.
3. Mark it `confirmed` and advance the write cursor in one local transaction.

A process can stop after the remote service accepts a batch but before SQLite records confirmation. On resume, fetch the destination from `destination_base_length` onward and compare its video-ID sequence with the planned sequence. Advance to the longest exact confirmed prefix. If the observed tail is not an exact prefix of the plan, pause with a destination-conflict error and do not add more tracks.

The user must not manually edit the destination while transfer is active. The UI states this before transfer. The app reliably detects changes that alter the destination length or the appended tail; edits confined to the older prefix may not be detectable and do not change the transferred sequence.

## 13. API Surface

The first stable API groups are:

- `/api/health` — backend and database status
- `/api/setup` — connection status and credential setup commands
- `/api/spotify/inspect` — validate and preview a public source URL
- `/api/youtube/playlists` — list eligible existing destinations
- `/api/transfers` — create and list jobs
- `/api/transfers/{id}` — job detail and aggregate progress
- `/api/transfers/{id}/commands` — start, pause, resume, cancel, begin transfer, or retry
- `/api/transfers/{id}/items` — paginated/filterable source and review data
- `/api/transfers/{id}/items/{item_id}/decision` — accept, search, select pasted URL, or skip
- `/api/transfers/{id}/events` — Server-Sent Events progress stream
- `/api/transfers/{id}/exports/{format}` — JSON or CSV report

Command requests include the last observed job revision. A stale revision returns a conflict response rather than applying an action to unexpected state.

## 14. Frontend Flow

1. **Setup:** enter the Spotify client ID, complete Spotify PKCE sign-in, initiate YouTube Music authentication, and run connection checks.
2. **Source:** paste the public Spotify URL and inspect playlist metadata.
3. **Destination:** create new or choose existing append-only; select visibility for a new destination.
4. **Matching:** follow progress and counts; pause or cancel safely.
5. **Review:** filter and resolve uncertain, unmatched, and unsupported positions.
6. **Transfer:** view ordered batch progress and clear recovery status.
7. **Report:** open the destination and export the result.
8. **History:** reopen previous jobs, resume incomplete work, retry recoverable failures, and inspect old reports.

The UI is keyboard-accessible, responsive at laptop widths, and does not render all 2,500 rows at once. Every long-running screen remains useful after an event-stream reconnection by refreshing canonical state from the API.

## 15. Reliability and Error Handling

- Retry transient network, 429, and eligible 5xx errors up to five times with exponential backoff and jitter.
- Do not retry authentication, validation, unsupported-content, or invariant errors automatically.
- Use conservative serial YouTube Music requests and connector-level throttling.
- Pause and request reauthentication when YouTube Music credentials expire.
- Preserve completed matching work if destination preparation or writing fails.
- Save an item-level failure reason and a safe user-facing summary.
- Detect unexpected destination length or appended-tail mutations and stop before compounding them.
- Allow cancellation between atomic connector calls; never terminate halfway through a local database transaction.
- On startup, mark abandoned active operations as recovery-required, then reconcile before resuming.

The application makes no promise about total transfer time because the unofficial service has no published quota contract. Progress is measured by completed positions and batches, not a precise clock estimate.

## 16. Credential and Data Security

- Bind the backend to loopback only by default.
- Store the Spotify client ID, Spotify PKCE tokens, Google OAuth client values, and YouTube Music authentication under the local runtime data directory, outside the repository.
- Restrict credential-file access to the current operating-system user where supported.
- Keep the runtime data directory outside the repository and commit only credential examples containing dummy values.
- Never include tokens, cookies, authorization headers, or raw authentication responses in logs, database events, API responses, or exports.
- Redact upstream error messages before surfacing them.
- Do not expose a network-listening mode in version one.

A hosted version requires a separate security design. Local credential storage, `ytmusicapi` authentication, and single-process jobs must not be reused unchanged for a public service.

## 17. Reporting

The final report includes:

- source and destination playlist metadata;
- counts for imported, unsupported, auto-accepted, manually resolved, skipped, transferred, and failed positions;
- one row per source position with source metadata, selected destination metadata, confidence, decision origin, and result;
- non-secret job warnings and timestamps;
- a direct destination playlist link.

CSV is flat and human-readable. JSON preserves the score breakdown and structured errors. Reports reflect the frozen source snapshot and remain available from job history.

## 18. Test Strategy

### Unit tests

- URL parsing, normalization, query construction, scoring, threshold boundaries, and version-marker penalties.
- State-machine transitions, cancellation boundaries, counters, and longest-prefix reconciliation.
- Exact handling of source duplicates and order.

### Connector contract tests

- Spotify fixtures cover pagination, snapshot changes, unavailable items, local files, episodes, malformed responses, authentication, and rate limits.
- YouTube Music tests use a dedicated small private test playlist and cover authentication, search result normalization, creation, append, listing, and common failures.
- Recorded responses are scrubbed of credentials and personal identifiers.

### Backend integration tests

- Database migrations and repository behavior.
- API validation and stale-revision conflicts.
- Pause/resume across each active state.
- Simulated crash before a send, after remote acceptance, and after local confirmation.
- Destination conflict detection.
- CSV and JSON report completeness.

### Frontend tests

- Setup, source inspection, destination selection, progress reconnection, review decisions, filtering, bulk actions, error states, and retry flows.
- Large synthetic review result sets verify responsiveness without rendering every row.

### End-to-end acceptance

Before the 2,500-track transfer, run a small controlled playlist containing exact songs, remasters, live versions, covers, duplicates, unavailable items, and one intentionally unmatched track. Confirm correct classification, manual resolution, exact accepted order, intentional duplicates, interruption recovery, destination link, and report exports.

## 19. Acceptance Criteria

Version one is complete when:

- A public Spotify playlist can be imported completely and frozen locally.
- At least 2,500 source positions can be stored, matched, reviewed, and reported without UI degradation.
- Matching decisions are explainable and strong matches follow the defined thresholds.
- No uncertain supported position is transferred without automatic qualification or explicit user approval.
- A new public or private YouTube Music playlist can be created, or an existing owned playlist can receive an append-only transfer.
- Accepted supported positions retain exact relative source order and intentional duplicates.
- Browser reloads do not stop or corrupt work.
- Backend interruption can be reconciled and resumed without unintended duplicate batches.
- Destination length or appended-tail divergence stops the transfer visibly.
- Unsupported, skipped, and failed items remain visible in history and exports.
- Credentials do not appear in frontend payloads, logs, database events, version control, or reports.
- The controlled end-to-end playlist passes before the large transfer begins.

## 20. Future Evolution

Potential follow-up designs may cover downloadable packaging, hosted accounts, official-provider alternatives, private Spotify playlists, multiple simultaneous jobs, bidirectional transfer, and ongoing synchronization. These are separate architectural projects. The version-one connector boundaries, API contract, and repository interfaces should make those projects possible without adding their complexity now.

## 21. External Constraints and References

- Spotify Web API authorization: <https://developer.spotify.com/documentation/web-api/concepts/authorization>
- Spotify Authorization Code with PKCE: <https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow>
- Spotify playlist-items endpoint and ownership constraint: <https://developer.spotify.com/documentation/web-api/reference/get-playlists-items>
- Spotify playlist concepts: <https://developer.spotify.com/documentation/web-api/concepts/playlists>
- Official YouTube playlist API: <https://developers.google.com/youtube/v3/guides/implementation/playlists>
- YouTube Data API quota overview: <https://developers.google.com/youtube/v3/getting-started>
- `ytmusicapi` project and capabilities: <https://github.com/sigma67/ytmusicapi>

`ytmusicapi` is explicitly unofficial and emulates YouTube Music web-client requests. Its speed is important for the initial 2,500-track use case, but its compatibility and authentication behavior may change independently of this application.
