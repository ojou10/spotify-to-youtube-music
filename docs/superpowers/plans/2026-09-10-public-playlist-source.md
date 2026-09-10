# Public Playlist Source Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let users without Spotify Premium create a durable source snapshot from a public Spotify URL or a local Spotify data export, then use the existing matching and transfer pipeline safely.

**Architecture:** Add a provider-neutral source boundary that produces a short-lived `SourceDraft` and ordered canonical track inputs. A normal public-page reader fails closed when Spotify does not expose a complete track list; a local export reader provides the reliable fallback. The destination step submits the draft ID, so the backend promotes the inspected snapshot into a durable transfer job without losing the source selection.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, SQLite, httpx, standard-library HTML/ZIP/JSON parsing, pytest, React 19, TypeScript 5, Vite, Vitest, Testing Library, npm.

## Global Constraints

- Accept a public Spotify playlist URL without requesting Spotify credentials, cookies, or Premium access.
- Never bypass Spotify authentication, rate limits, bot protections, or access controls.
- Never collect or store Spotify browser cookies.
- Preserve source order and intentional duplicates.
- Detect incomplete or blocked extraction instead of silently transferring partial data.
- Accept only user-selected local export files and parse them outside the repository.
- Never commit, upload, or log ZIP contents, tokens, cookies, authorization codes, or client secrets.
- Runtime secrets, SQLite data, and temporary exports stay in the operating-system application-data directory.
- A supported item must be auto-accepted, manually accepted, or explicitly skipped before destination writing starts.
- Keep one durable worker and one remote operation at a time.
- Keep the backend bound to 127.0.0.1 only.
- Run tests before implementation for each task, run the narrow suite first, and commit each completed task.
- Public documentation contains dummy credential examples only and states that ytmusicapi is unofficial.

---

## File Map

### Backend source boundary

- Create: `backend/app/sources/base.py` — source reader protocols, canonical inputs, and source errors.
- Create: `backend/app/sources/public_spotify.py` — normal public-page fetch and fail-closed extraction.
- Create: `backend/app/sources/spotify_export.py` — safe ZIP/JSON validation and playlist extraction.
- Create: `backend/app/sources/drafts.py` — source draft service and expiry rules.
- Modify: `backend/app/domain/enums.py` — source kind enum.
- Modify: `backend/app/domain/models.py` — source preview/input/draft DTOs.

### Persistence and API

- Modify: `backend/app/persistence/tables.py` — `SourceDraftRow` and `SourceDraftItemRow` tables.
- Modify: `backend/app/persistence/repositories.py` — draft create/read/delete and promotion helpers.
- Create: `backend/alembic/versions/20260910_add_source_drafts.py` — migration.
- Create: `backend/app/api/sources.py` — provider-neutral inspect and export-upload routes.
- Modify: `backend/app/api/transfers.py` — accept `source_draft_id` and retain compatibility validation.
- Modify: `backend/app/transfer/service.py` — promote a validated draft into the frozen job snapshot.
- Modify: `backend/app/main.py` — register the source router and dependencies.
- Modify: `backend/pyproject.toml` — add `python-multipart` for bounded multipart uploads.

### Frontend

- Modify: `frontend/src/api/types.ts` — source preview/draft and upload response types.
- Modify: `frontend/src/features/source/SourcePage.tsx` — source-mode tabs, export upload, completeness status, and draft navigation.
- Modify: `frontend/src/features/destination/DestinationPage.tsx` — read `draft_id` from the URL and submit it.
- Modify: `frontend/src/App.tsx` — preserve destination query parameters during routing.

### Tests and fixtures

- Create: `backend/tests/sources/test_public_spotify.py` — public-page parser and completeness fixtures.
- Create: `backend/tests/sources/test_spotify_export.py` — JSON/ZIP parser and archive safety tests.
- Create: `backend/tests/sources/test_drafts.py` — expiry and promotion tests.
- Create: `backend/tests/api/test_sources.py` — inspect/upload/error contracts.
- Modify: `backend/tests/api/test_destinations.py` — draft-based destination creation.
- Modify: `backend/tests/integration/test_source_import.py` — canonical snapshot promotion.
- Create: `backend/tests/fixtures/public_spotify_page.html` — synthetic public page with ordered tracks and a duplicate.
- Create: `backend/tests/fixtures/spotify_export_playlist.json` — synthetic export with names, artists, albums, order, and duplicate entries.
- Create: `backend/tests/fixtures/spotify_export_malformed.json` — malformed export cases.
- Modify: `frontend/src/App.test.tsx` or add colocated source/destination tests — draft navigation and upload states.

---

## Task 1: Canonical Source Inputs and Durable Draft Persistence

**Files:**
- Create: `backend/app/sources/base.py`
- Create: `backend/app/sources/drafts.py`
- Modify: `backend/app/domain/enums.py`, `backend/app/domain/models.py`
- Modify: `backend/app/persistence/tables.py`, `backend/app/persistence/repositories.py`
- Create: `backend/alembic/versions/20260910_add_source_drafts.py`
- Test: `backend/tests/sources/test_drafts.py`

**Interfaces:**

- `SourceKind = Literal["public_url", "spotify_export", "spotify_api"]`
- `SourceTrackInput(position: int, title: str, artists: tuple[str, ...], album: str | None, duration_ms: int | None, source_ref: str | None)`
- `SourcePreview(draft_id: str, kind: SourceKind, name: str | None, owner_name: str | None, declared_total: int | None, observed_total: int, complete: bool, issues: tuple[str, ...])`
- `SourceDraftService.create(kind, source_ref, name, owner_name, declared_total, items) -> SourcePreview`
- `SourceDraftService.get_complete(draft_id) -> tuple[SourcePreview, list[SourceTrackInput]]`
- `SourceDraftService.delete_expired(now) -> int`
- Later tasks consume `SourceDraftService.get_complete`; the transfer service promotes its items into existing `SourceItemRow` rows.

- [ ] **Step 1: Write failing draft tests**

```python
def test_draft_round_trips_order_and_duplicates(draft_service):
    items = [
        SourceTrackInput(0, "Song", ("Artist",), "Album", 180000, None),
        SourceTrackInput(1, "Song", ("Artist",), "Album", 180000, None),
    ]
    preview = draft_service.create("public_url", "spotify:playlist:demo", "Demo", None, 2, items)
    loaded_preview, loaded_items = draft_service.get_complete(preview.draft_id)
    assert loaded_preview.observed_total == 2
    assert [item.position for item in loaded_items] == [0, 1]
    assert loaded_items[0].title == loaded_items[1].title


def test_expired_draft_cannot_be_promoted(draft_service, clock):
    preview = draft_service.create("spotify_export", None, "Demo", None, 0, [])
    clock.advance(minutes=31)
    with pytest.raises(SourceDraftExpired):
        draft_service.get_complete(preview.draft_id)
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/sources/test_drafts.py -q`

Expected: import/fixture failures because the source package and draft tables do not exist.

- [ ] **Step 3: Implement canonical DTOs and persistence**

Add the source kind enum, dataclasses, SQLAlchemy rows, repository methods, and Alembic migration. Store draft metadata and items in SQLite, set an explicit 30-minute expiry, and reject non-contiguous positions, empty titles, or empty artist tuples before insertion. Serialize artists as JSON using the existing repository conventions.

- [ ] **Step 4: Run the focused tests and then persistence tests**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/sources/test_drafts.py backend/tests/persistence -q`

Expected: all focused tests pass and existing persistence tests remain green.

- [ ] **Step 5: Commit the canonical source boundary**

```powershell
git add backend/app/sources backend/app/domain backend/app/persistence backend/alembic backend/tests/sources/test_drafts.py
git commit -m "feat: add canonical source drafts"
```

---

## Task 2: Public Spotify URL Feasibility Reader

**Files:**
- Create: `backend/app/sources/public_spotify.py`
- Create: `backend/tests/sources/test_public_spotify.py`
- Create: `backend/tests/fixtures/public_spotify_page.html`
- Modify: `backend/app/connectors/base.py` only if a shared safe HTTP error is needed.

**Interfaces:**

- `PublicSpotifyReader(http_client: httpx.AsyncClient, drafts: SourceDraftService)`
- `PublicSpotifyReader.inspect(url: str) -> SourcePreview`
- `PublicSpotifyReader._parse_public_document(html: str, url: str) -> ParsedPublicPlaylist`
- `ParsedPublicPlaylist(name: str | None, owner_name: str | None, declared_total: int | None, items: list[SourceTrackInput], issues: tuple[str, ...])`
- Produces `incomplete_public_source` when the page is blocked, requires login, lacks ordered items, or has a count mismatch.
- It never accepts cookies, authorization headers, or caller-supplied browser sessions.

- [ ] **Step 1: Write failing parser tests**

```python
def test_public_page_parser_preserves_order_and_duplicate(reader, fixture_text):
    parsed = reader._parse_public_document(fixture_text, "https://open.spotify.com/playlist/demo")
    assert parsed.name == "Demo playlist"
    assert [item.position for item in parsed.items] == [0, 1, 2]
    assert parsed.items[0].title == parsed.items[2].title
    assert parsed.items[1].duration_ms == 201000


def test_missing_track_data_fails_closed(reader):
    parsed = reader._parse_public_document("<html><body>Log in</body></html>", "https://open.spotify.com/playlist/demo")
    assert "incomplete_public_source" in parsed.issues
    assert parsed.items == []
```

- [ ] **Step 2: Run the parser tests and verify they fail**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/sources/test_public_spotify.py -q`

Expected: missing reader/parser failures.

- [ ] **Step 3: Implement URL validation and normal public fetch**

Accept only `open.spotify.com/playlist/<id>`, `play.spotify.com/playlist/<id>`, and `spotify:playlist:<id>` forms. Use an `httpx.AsyncClient` with a bounded timeout and a normal public `GET`; do not attach Spotify OAuth headers or cookies. Translate 403, 429, 5xx, redirects to login, and empty documents into safe source issues.

- [ ] **Step 4: Implement conservative document parsing**

Parse only data explicitly present in the returned document: JSON-LD, `__NEXT_DATA__`, or equivalent embedded track objects with title, artists, album, duration, and position. Do not execute JavaScript or infer missing tracks from page text. Normalize durations to milliseconds, reject duplicate positions, retain duplicate tracks at distinct positions, and compare observed versus declared totals.

- [ ] **Step 5: Persist complete results as drafts and expose failure reasons**

On a complete parse, call `SourceDraftService.create("public_url", canonical_url, ...)`. On an incomplete parse, return a preview with `complete=false` and a stable issue code without creating a transferable draft. Do not log the HTML body or raw response.

- [ ] **Step 6: Run focused and full source tests**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/sources/test_public_spotify.py backend/tests/sources/test_drafts.py -q`

Expected: all tests pass.

- [ ] **Step 7: Commit the public reader**

```powershell
git add backend/app/sources/public_spotify.py backend/tests/sources/test_public_spotify.py backend/tests/fixtures/public_spotify_page.html
 git commit -m "feat: add fail-closed public Spotify reader"
```

---

## Task 3: Local Spotify Export Reader and Archive Safety

**Files:**
- Create: `backend/app/sources/spotify_export.py`
- Create: `backend/tests/sources/test_spotify_export.py`
- Create: `backend/tests/fixtures/spotify_export_playlist.json`
- Create: `backend/tests/fixtures/spotify_export_malformed.json`
- Modify: `backend/pyproject.toml`

**Interfaces:**

- `SpotifyExportReader(drafts: SourceDraftService, temp_root: Path, max_upload_bytes: int = 25_000_000, max_uncompressed_bytes: int = 100_000_000)`
- `SpotifyExportReader.inspect_json(payload: bytes, filename: str) -> SourcePreview`
- `SpotifyExportReader.inspect_zip(payload: bytes, filename: str) -> SourcePreview`
- `SpotifyExportReader._parse_playlist_records(records: object) -> ParsedExportPlaylist`
- Produces stable issue codes: `unsupported_export`, `malformed_export`, `archive_too_large`, `archive_path_traversal`, and `incomplete_export`.

- [ ] **Step 1: Write failing export and safety tests**

```python
def test_export_parser_preserves_order_and_duplicate(export_reader, fixture_bytes):
    preview = export_reader.inspect_json(fixture_bytes, "playlist.json")
    items = export_reader.drafts.get_complete(preview.draft_id)[1]
    assert [item.position for item in items] == [0, 1, 2]
    assert items[0].title == items[2].title


def test_zip_path_traversal_is_rejected(export_reader, traversal_zip):
    preview = export_reader.inspect_zip(traversal_zip, "spotify.zip")
    assert preview.complete is False
    assert "archive_path_traversal" in preview.issues
```

- [ ] **Step 2: Run focused tests and verify failure**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/sources/test_spotify_export.py -q`

Expected: missing parser and safety failures.

- [ ] **Step 3: Add bounded multipart support**

Add `python-multipart` to the backend dependencies. Enforce the byte limit before parsing and reject filenames that are not `.json` or `.zip`. Use `zipfile.ZipFile` without extracting to the repository; reject absolute paths, `..` components, symlinks, and cumulative uncompressed size over 100 MB.

- [ ] **Step 4: Implement JSON and ZIP discovery**

For JSON, accept the documented playlist representation and locate playlist records by structural keys, not arbitrary text matching. For ZIP, inspect members in memory or a temporary application-data directory, select JSON files whose records contain playlist names and track arrays, and delete temporary files in a `finally` block. Never return raw export contents in API responses.

- [ ] **Step 5: Map records to canonical inputs**

Read song name, artist name(s), album/episode name, and duration when available. Generate contiguous source positions in record order. Preserve repeated records. Mark local files and podcast episodes as unsupported items rather than dropping positions. Reject records without a title or artist and return `incomplete_export` when no valid playlist can be identified.

- [ ] **Step 6: Run focused and full backend tests**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/sources/test_spotify_export.py backend/tests/sources backend/tests -q`

Expected: all tests pass, with the existing live tests still opt-in skipped.

- [ ] **Step 7: Commit the export reader**

```powershell
git add backend/app/sources/spotify_export.py backend/pyproject.toml backend/tests/sources backend/tests/fixtures
 git commit -m "feat: import Spotify data exports safely"
```

---

## Task 4: Source API, Draft Promotion, and Transfer Handoff

**Files:**
- Create: `backend/app/api/sources.py`
- Modify: `backend/app/api/transfers.py`, `backend/app/transfer/service.py`, `backend/app/main.py`, `backend/app/persistence/repositories.py`
- Create: `backend/tests/api/test_sources.py`
- Modify: `backend/tests/api/test_destinations.py`, `backend/tests/integration/test_source_import.py`

**Interfaces:**

- `POST /api/sources/inspect` body `{ "url": "..." }` -> `SourcePreview`
- `POST /api/sources/export` multipart field `file` -> `SourcePreview`
- `POST /api/transfers` body includes `source_draft_id` and destination fields; an empty `source_url` is rejected.
- `TransferService.import_draft(draft_id: str, destination: DestinationSpec) -> TransferJob`
- The legacy `POST /api/spotify/inspect` route may call the compatibility reader but cannot create a job from an empty URL.

- [ ] **Step 1: Write failing API and handoff tests**

```python
def test_inspect_returns_draft_id(client, public_reader):
    response = client.post("/api/sources/inspect", json={"url": "https://open.spotify.com/playlist/demo"})
    assert response.status_code == 200
    assert response.json()["draft_id"]
    assert response.json()["complete"] is True


def test_transfer_requires_source_draft(client):
    response = client.post("/api/transfers", json={"source_url": "", "destination_mode": "create", "destination_name": "Demo"})
    assert response.status_code == 422
```

- [ ] **Step 2: Run focused API tests and verify failure**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/api/test_sources.py backend/tests/api/test_destinations.py backend/tests/integration/test_source_import.py -q`

Expected: missing source routes and draft promotion failures.

- [ ] **Step 3: Implement source routes and dependency wiring**

Register `sources_router` in `main.py`. Use the existing app-state database and source services. Return stable error envelopes for blocked/incomplete sources, unsupported files, and expired drafts. Cap upload size before handing bytes to the export reader.

- [ ] **Step 4: Promote drafts into durable jobs**

Update the transfer request model to require a valid `source_draft_id` for the new route. In one short transaction, load the draft, validate expiry/completeness, copy metadata and ordered items into the existing job/source-item rows, and mark the draft consumed so it cannot create a second job. Keep legacy `source_url` support only when it is non-empty and explicitly routed through the existing API connector.

- [ ] **Step 5: Preserve destination requirements**

Validate that a draft source and destination fields are both present before creating a job. Do not start matching until the job has a destination specification. Keep existing owner checks, append-only behavior, and unresolved-item gating.

- [ ] **Step 6: Run affected and full backend suites**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/api/test_sources.py backend/tests/api/test_destinations.py backend/tests/integration/test_source_import.py -q` and then `backend\.venv\Scripts\python.exe -m pytest backend/tests -q`.

Expected: all backend tests pass.

- [ ] **Step 7: Commit the source API and handoff**

```powershell
git add backend/app/api/sources.py backend/app/api/transfers.py backend/app/transfer/service.py backend/app/main.py backend/app/persistence/repositories.py backend/tests/api backend/tests/integration/test_source_import.py
 git commit -m "feat: promote source drafts into transfers"
```

---

## Task 5: Source and Destination UI for URL or Export Mode

**Files:**
- Modify: `frontend/src/api/types.ts`, `frontend/src/features/source/SourcePage.tsx`, `frontend/src/features/destination/DestinationPage.tsx`, `frontend/src/App.tsx`
- Create or modify: `frontend/src/features/source/SourcePage.test.tsx`, `frontend/src/features/destination/DestinationPage.test.tsx`

**Interfaces:**

- `SourcePreview` includes `draft_id`, `kind`, `complete`, `observed_total`, and `issues`.
- Source page calls `api.post<SourcePreview>("/sources/inspect", { url })` for URL mode and `api.upload<SourcePreview>("/sources/export", file)` for export mode.
- Destination page reads `new URLSearchParams(window.location.search).get("draft_id")` and sends `{ source_draft_id: draftId, destination_mode, ... }`.

- [ ] **Step 1: Write failing UI tests**

```tsx
it("navigates a complete URL draft to destination", async () => {
  server.use(inspectSource.mockResolvedValue({ draft_id: "draft-1", complete: true, observed_total: 3 }));
  await user.type(screen.getByLabelText(/spotify playlist url/i), "https://open.spotify.com/playlist/demo");
  await user.click(screen.getByRole("button", { name: /inspect playlist/i }));
  await user.click(await screen.findByRole("link", { name: /continue to destination/i }));
  expect(window.location.pathname).toBe("/new/destination");
  expect(window.location.search).toContain("draft_id=draft-1");
});
```

- [ ] **Step 2: Run focused frontend tests and verify failure**

Run: `npm --prefix frontend test -- --run src/features/source/SourcePage.test.tsx src/features/destination/DestinationPage.test.tsx`

Expected: missing source mode, upload client, draft query, and request assertions.

- [ ] **Step 3: Implement source-mode selection**

Add a clear `Public Spotify URL` / `Spotify data export` selector. URL mode validates the supported public URL shape. Export mode accepts `.json` and `.zip`, shows the local-only privacy note, and disables submission while uploading. Display playlist name, owner, observed/declared counts, completeness, and actionable issue text.

- [ ] **Step 4: Implement draft-aware destination creation**

Read and validate `draft_id` from the URL. Disable **Create transfer** when it is missing or the source preview is incomplete. Submit the draft ID with destination name, visibility, and mode. For append mode, submit the selected owned playlist ID. On success, navigate to `/jobs/<id>/progress`.

- [ ] **Step 5: Add safe loading and error states**

Do not show export bytes, credentials, or raw provider responses. Explain that a blocked public page requires the export fallback. Keep private visibility selected by default and preserve the existing append-only warning.

- [ ] **Step 6: Run frontend quality checks**

Run: `npm --prefix frontend test -- --run`, `npm --prefix frontend run lint`, and `npm --prefix frontend run build`.

Expected: all tests, type checks, and production build pass.

- [ ] **Step 7: Commit the UI handoff**

```powershell
git add frontend/src
 git commit -m "feat: add public source and export flow"
```

---

## Task 6: Documentation, Opt-In Feasibility Probe, and Release Gate

**Files:**
- Modify: `README.md`, `docs/setup.md`, `docs/test-playlist.md`, `docs/architecture.md`
- Create: `backend/tests/contract/test_live_public_source.py`
- Modify: `package.json`, `scripts/check-secrets.ps1`

**Interfaces:**

- `PLAYLIST_BRIDGE_LIVE_TESTS=1` enables a read-only public URL probe; default test runs skip it.
- `npm run verify` remains the single local release gate and includes the new source tests.

- [ ] **Step 1: Write the opt-in public-source contract test**

```python
@pytest.mark.skipif(os.getenv("PLAYLIST_BRIDGE_LIVE_TESTS") != "1", reason="opt-in public source probe")
def test_public_source_probe_does_not_write(live_reader, public_playlist_url):
    preview = live_reader.inspect(public_playlist_url)
    assert preview.kind == "public_url"
    assert preview.observed_total >= 1
```

The test must use an explicitly supplied public URL, never print the URL’s query string, and never authenticate or write to either provider.

- [ ] **Step 2: Run the contract test in default mode**

Run: `backend\.venv\Scripts\python.exe -m pytest backend/tests/contract/test_live_public_source.py -q`

Expected: skipped with a clear opt-in message.

- [ ] **Step 3: Update documentation**

Document the two source modes, the fail-closed public URL behavior, the Spotify export request path, the 30-minute draft lifetime, the fact that order/duplicates must be verified on a small sample, and the Premium restriction on the legacy Spotify API path. State that YouTube Music still requires the Google device OAuth setup and that ytmusicapi is unofficial.

- [ ] **Step 4: Update the release gate**

Ensure `npm run verify` runs backend source tests, API/integration tests, frontend tests, lint, build, the secret/artifact scan, and `git diff --check`. Keep live provider tests opt-in and ensure tracked-file scanning excludes only the scanner’s own detection-pattern file.

- [ ] **Step 5: Run the complete gate**

Run: `npm run verify`

Expected: all automated checks pass; live provider tests remain skipped unless explicitly enabled.

- [ ] **Step 6: Review the tracked surface**

Run: `git status --short`, `git ls-files`, and `git grep -n -I -E "access_token|refresh_token|client_secret|BEGIN .*PRIVATE KEY"`. Inspect every match and confirm it is code, a dummy test value, or security documentation. Confirm no export, SQLite, OAuth, browser, or build artifact is tracked.

- [ ] **Step 7: Commit and push the release-gate changes**

```powershell
git add README.md docs scripts package.json backend/tests/contract/test_live_public_source.py
git commit -m "feat: support no-premium public playlist sources"
git push origin main
```

---

## Execution Order and Review Gates

Execute Tasks 1–6 in order. Stop after Task 2 for the public-page feasibility result. If the real public page is incomplete, continue with Task 3 and treat export mode as the reliable source. Stop after Task 4 for an API/integration checkpoint, after Task 5 for a UI checkpoint, and after Task 6 for the manual controlled small-playlist acceptance. Do not begin the 2,500-track transfer until the source count, order, duplicates, matching review, destination result, and reconciliation report have all been verified.

## Reference Documentation

- Design: `docs/superpowers/specs/2026-09-10-public-playlist-source-design.md`
- Spotify data export: https://support.spotify.com/in-en/article/understanding-your-data/
- Spotify playlist privacy: https://support.spotify.com/sm-en/article/playlist-privacy-and-access/
- YouTube Music OAuth connector: `backend/app/connectors/ytmusic_auth.py`
- Existing matching contract: `backend/app/matching/score.py`
- Existing transfer recovery: `backend/app/transfer/reconcile.py`