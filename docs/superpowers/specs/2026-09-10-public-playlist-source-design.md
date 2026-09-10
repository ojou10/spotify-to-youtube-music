# Public Playlist Source and Export Fallback Design

## Status

Approved in chat for design drafting; implementation has not started.

## Problem

Spotify Development Mode now requires Premium for the Web API. The current Spotify OAuth source path therefore cannot support the intended no-Premium, eventual public-user experience. Users should be able to provide a public Spotify playlist URL, while retaining a reliable fallback for Spotify's own data export.

## Goals

- Accept a public Spotify playlist URL without requesting Spotify credentials, cookies, or Premium access.
- Extract the metadata needed for matching: source position, title, artist names, album, and duration when available.
- Preserve source order and intentional duplicates.
- Detect incomplete or blocked extraction instead of silently transferring partial data.
- Offer a local Spotify data-export import fallback.
- Reuse the existing matching, review, transfer, recovery, and reporting pipeline.
- Keep user data and uploaded exports outside the repository and out of logs.
- Make source selection durable so the destination step receives the inspected source snapshot.

## Non-goals

- Bypassing Spotify authentication, rate limits, bot protections, or access controls.
- Reading private Spotify playlists from a URL.
- Collecting or storing Spotify browser cookies.
- Building a hosted multi-user scraper in this iteration.
- Guaranteeing that Spotify's export contains fields that Spotify does not provide.

## User experience

1. User opens New transfer.
2. User pastes a public Spotify playlist URL.
3. Playlist Bridge attempts a best-effort public metadata read.
4. The app displays an eligibility result with playlist name, owner when available, count, and completeness status.
5. If the result is complete, the user continues to destination selection.
6. If the result is blocked or incomplete, the app explains why and offers a Spotify data-export upload.
7. The export is parsed locally, previewed, and converted into the same frozen source snapshot format.
8. The user chooses a new or owned append-only YouTube Music destination.
9. The transfer job runs through the existing matching, review, batching, recovery, and reporting flow.

The first real acceptance test uses a small public playlist. The 2,500-track playlist is not started until the source count and completeness checks pass.

## Architecture

### Source boundary

Add a provider-neutral source interface that returns canonical playlist metadata and ordered track inputs:

```text
SourceReader.inspect(input) -> SourcePreview
SourceReader.import_snapshot(input) -> FrozenSourceSnapshot
```

Implement two readers:

- `PublicSpotifyReader`: accepts only public Spotify playlist URLs and performs a normal public-page read. It must fail closed when the page is blocked, requires login, or does not expose a complete ordered track list.
- `SpotifyExportReader`: accepts a user-selected ZIP or JSON export, validates it, and extracts playlist entries locally. It must reject path traversal, oversized archives, unsupported file types, and malformed records.

The existing Spotify Web API connector may remain as a compatibility path, but it is not required for the no-Premium workflow and must not be presented as the default.

### Canonical source data

Both readers map to the existing source-item model:

- stable source position
- title
- ordered artist names
- album name when present
- duration in milliseconds when present
- source kind (`public_url` or `spotify_export`)
- optional source reference, never an access token or cookie

The frozen snapshot is the source of truth for later matching and reporting. Missing duration is allowed and lowers match confidence; missing title or artists is rejected as unusable.

### Completeness validation

Before a snapshot becomes eligible:

- positions must be contiguous from zero;
- the observed count must equal the declared count when a declared count exists;
- duplicates must remain separate positions;
- every accepted item must have a non-empty title and at least one artist;
- unsupported local files or podcast episodes are represented as skipped items, not silently dropped;
- a partial or ambiguous extraction returns a recoverable error and never creates a transfer job.

### Transfer handoff

The source preview must persist a short-lived source selection or snapshot identifier. The destination page submits that identifier, not an empty source URL. The backend validates that the snapshot belongs to the pending transfer and then creates the durable job. Refreshing or navigating between source and destination must not lose the source selection.

### Existing pipeline reuse

After source ingestion, no changes are required to the core matching contract:

```text
frozen source snapshot
  -> deterministic YouTube Music queries
  -> scored candidates
  -> automatic/review/unmatched classification
  -> user decisions
  -> destination preparation
  -> persisted append batches
  -> reconciliation and report
```

## Public-page extraction strategy

The reader may use a normal HTTP fetch and parser for the initial feasibility probe. If the page does not contain the complete track data without executing client-side code, the reader must report `incomplete_public_source` rather than inventing data. A browser-rendered extractor can be evaluated later behind the same interface, but it must not use the user's personal browser profile or cookies.

This boundary keeps the product honest: a public URL is accepted only when the returned data is complete enough to preserve playlist meaning.

## Export parsing and privacy

- Accept only user-selected local files through the app.
- Parse in a temporary operating-system application-data directory.
- Never commit, upload, or log the ZIP contents.
- Remove temporary extracted files after parsing or explicit failure cleanup.
- Store only the frozen source snapshot and derived metadata required for the job.
- Document that Spotify's export fields and ordering must be verified against a small sample before a large transfer.

## API/UI changes

- Add a provider-neutral source inspection/import route while retaining a compatibility wrapper for the current Spotify inspection route.
- Add an export upload route with size and file-type validation.
- Update the source page to show the source mode and completeness result.
- Update destination creation to receive the persisted source selection.
- Keep the existing setup page for YouTube Music; Spotify credentials become optional and are not needed for public URL/export mode.
- Show actionable errors for blocked/incomplete public reads and Premium-restricted OAuth attempts.

## Testing and acceptance

- Unit tests for URL validation, public-page parsing, export JSON parsing, duplicate/order preservation, missing-field handling, and archive safety.
- API tests for inspection, upload, completeness rejection, and source-to-destination handoff.
- Integration tests proving the canonical snapshot feeds the existing matcher and transfer worker.
- Fixture-based tests must contain no personal playlist data or credentials.
- An opt-in live probe may test a public URL read-only; it must never write to Spotify or YouTube Music.
- Manual acceptance: a small public playlist or export is inspected, transferred to a new private YouTube Music playlist, and reconciled before attempting the large playlist.

## Risks and mitigations

- **Dynamic or blocked Spotify pages:** fail closed, explain the limitation, and offer export fallback.
- **Export schema changes:** version the parser, retain fixtures, and show an actionable unsupported-format error.
- **Large files or archives:** enforce upload and extraction limits before parsing.
- **Privacy leakage:** local-only temporary files, redacted logs, ignored runtime paths, and secret scanning.
- **User expectation of exact equivalence:** show source count, skipped items, uncertain matches, and final reconciliation report.

## Deferred work

- Hosted public scraping service and multi-user authentication.
- Continuous synchronization.
- Private playlist URL access.
- Additional music providers.
- Full browser end-to-end automation.

## Success criteria

A user without Spotify Premium can paste a public playlist URL or select a Spotify data export, obtain a complete ordered source snapshot without sharing Spotify credentials, and safely transfer a controlled small playlist to YouTube Music using the existing reviewable and resumable pipeline.