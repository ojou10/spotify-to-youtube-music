# Spotify to YouTube Music Transfer App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (- [ ]) syntax for tracking.

**Goal:** Build a local, resumable React and FastAPI application that transfers an owned public Spotify playlist to a new or existing YouTube Music playlist while preserving order and intentional duplicates.

**Architecture:** A React/TypeScript client talks only to a loopback FastAPI API. FastAPI coordinates isolated Spotify and YouTube Music connectors, a pure matching engine, a durable single-worker state machine, and SQLite repositories; Server-Sent Events carry progress while REST remains canonical.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic 2, SQLAlchemy 2, Alembic, SQLite, httpx, RapidFuzz, platformdirs, ytmusicapi, pytest, React 19, TypeScript 5, Vite, React Router, TanStack Query, Vitest, Testing Library, Playwright, npm.

## Global Constraints

- Bind the backend to 127.0.0.1 only; do not add a network-listening mode.
- Store the SQLite database and all OAuth material in the per-user platform application-data directory, never in the repository.
- Never log, return, export, fixture-record, or commit secrets, cookies, tokens, authorization codes, or raw authentication responses.
- Spotify sources must be public playlists owned by the connected Spotify user.
- Spotify authentication must use Authorization Code with PKCE and must not require a Spotify client secret.
- Pin ytmusicapi in the backend lock file and keep all of its calls inside one connector package.
- Run one durable worker and one remote operation at a time.
- Preserve source position and intentional duplicates; existing YouTube Music destinations are append-only.
- A supported item must be auto-accepted, manually accepted, or explicitly skipped before destination writing starts.
- Use short SQLite transactions, WAL mode, schema migrations, deterministic scoring, conservative serial YouTube Music requests, and bounded retry with jitter.
- Treat the backend as canonical state; browser refresh or SSE reconnect must not alter a job.
- Add tests before implementation, run the narrow test first, then the affected suite, and commit each completed task.
- Public documentation must contain dummy credential examples only and must state that ytmusicapi is unofficial.

---

## File Map

### Repository and tooling

- .gitignore — excludes runtime data, OAuth files, environment files, caches, builds, and editor artifacts.
- .editorconfig — consistent UTF-8, final newlines, and indentation.
- README.md — public overview, status, safety statement, and development entry points.
- SECURITY.md — private vulnerability reporting and accidental-secret response.
- CONTRIBUTING.md — setup, test, commit, and disclosure rules.
- LICENSE — MIT license.
- package.json — root npm orchestration commands.

### Backend

- backend/pyproject.toml — Python package, dependency groups, and pytest configuration.
- backend/app/main.py — FastAPI application factory and lifespan.
- backend/app/api/errors.py — stable API error envelope and exception handlers.
- backend/app/api/health.py — health endpoint.
- backend/app/api/setup.py — Spotify and YouTube Music connection endpoints.
- backend/app/api/spotify.py — source inspection endpoint.
- backend/app/api/transfers.py — job commands, items, history, events, and exports.
- backend/app/domain/enums.py — persistent status enums.
- backend/app/domain/models.py — connector-neutral dataclasses and scoring values.
- backend/app/domain/state_machine.py — legal transfer transitions.
- backend/app/settings/paths.py — platform application-data paths.
- backend/app/settings/secrets.py — atomic credential storage and redaction.
- backend/app/connectors/base.py — connector protocols and stable connector errors.
- backend/app/connectors/spotify_auth.py — PKCE, callback state, token exchange, and refresh.
- backend/app/connectors/spotify.py — Spotify Web API metadata and item pagination.
- backend/app/connectors/ytmusic_auth.py — Google device-code setup for ytmusicapi.
- backend/app/connectors/ytmusic.py — search, playlist listing, creation, retrieval, and append.
- backend/app/matching/normalize.py — metadata and version-marker normalization.
- backend/app/matching/queries.py — deterministic search-query construction.
- backend/app/matching/score.py — candidate scoring and classification.
- backend/app/persistence/db.py — SQLAlchemy engine, WAL configuration, and sessions.
- backend/app/persistence/tables.py — ORM tables.
- backend/app/persistence/repositories.py — job, source-item, candidate, batch, and event repositories.
- backend/app/transfer/retry.py — retry policy and redacted connector failures.
- backend/app/transfer/service.py — use cases and command validation.
- backend/app/transfer/worker.py — durable single-worker loop.
- backend/app/transfer/reconcile.py — longest-prefix destination recovery.
- backend/app/reporting/export.py — CSV and JSON reports.
- backend/alembic.ini and backend/migrations/ — schema migration configuration and revisions.
- backend/tests/ — unit, contract, integration, and API tests mirroring the app packages.

### Frontend

- frontend/package.json — frontend dependencies and scripts.
- frontend/vite.config.ts — Vite, test environment, proxy, and coverage configuration.
- frontend/src/main.tsx — React bootstrap.
- frontend/src/app/router.tsx — route tree.
- frontend/src/app/queryClient.ts — TanStack Query defaults.
- frontend/src/api/client.ts — typed JSON requests and ApiError.
- frontend/src/api/types.ts — API contract types.
- frontend/src/api/events.ts — reconnecting SSE subscription.
- frontend/src/components/ — reusable status, progress, table, dialog, and form controls.
- frontend/src/features/setup/ — provider setup and connection status.
- frontend/src/features/source/ — Spotify URL inspection and preview.
- frontend/src/features/destination/ — create/append destination settings.
- frontend/src/features/progress/ — live matching and transfer progress.
- frontend/src/features/review/ — virtualized review grid, search, decisions, and bulk actions.
- frontend/src/features/history/ — saved jobs and resume actions.
- frontend/src/features/report/ — summary and export links.
- frontend/src/styles/ — tokens, global styles, and accessible focus rules.
- frontend/src/test/ — shared test server and render helpers.
- frontend/e2e/ — Playwright happy-path, recovery, and disclosure-safety tests.

## Shared Interfaces

The first implementation tasks establish these names; later tasks must consume them without renaming:

~~~python
class SpotifyConnector(Protocol):
    def current_user(self) -> SpotifyUser: ...
    def inspect_playlist(self, playlist_id: str) -> PlaylistPreview: ...
    def iter_playlist_items(self, playlist_id: str, start: int = 0) -> Iterator[SourceItem]: ...

class YouTubeMusicConnector(Protocol):
    def search_songs(self, query: str, limit: int = 5) -> list[YTMCandidate]: ...
    def list_owned_playlists(self) -> list[DestinationPlaylist]: ...
    def get_playlist_video_ids(self, playlist_id: str) -> list[str]: ...
    def create_playlist(self, name: str, description: str, visibility: Visibility) -> str: ...
    def append_video_ids(self, playlist_id: str, video_ids: list[str]) -> None: ...

class MatchResult(NamedTuple):
    classification: MatchStatus
    selected_video_id: str | None
    candidates: list[ScoredCandidate]

class TransferService:
    def create_job(self, request: CreateJob) -> UUID: ...
    def command(self, job_id: UUID, revision: int, command: JobCommand) -> TransferJob: ...
    def decide(self, job_id: UUID, item_id: UUID, decision: ReviewDecision) -> SourceItem: ...
~~~

Frontend requests use ApiError with code, message, action, and optional field_errors. Every mutable job command carries revision.

---

### Task 1: Public Repository Foundation and Running Shell

**Files:**
- Create: .gitignore, .editorconfig, README.md, SECURITY.md, CONTRIBUTING.md, LICENSE, package.json
- Create: backend/pyproject.toml, backend/app/__init__.py, backend/app/main.py, backend/app/api/health.py, backend/app/spa.py
- Create: backend/tests/conftest.py, backend/tests/api/test_health.py
- Create: frontend/package.json, frontend/index.html, frontend/tsconfig.json, frontend/vite.config.ts
- Create: frontend/src/main.tsx, frontend/src/App.tsx, frontend/src/App.test.tsx, frontend/src/test/setup.ts

**Interfaces:**
- Produces: create_app() -> FastAPI and GET /api/health -> {"status": "ok"}
- Produces: root scripts dev, test, test:backend, test:frontend, lint, and build

- [ ] **Step 1: Add public-safe repository files and dependency manifests**

Use Python >=3.12 and Node >=22. Backend runtime dependencies are FastAPI, uvicorn, pydantic-settings, SQLAlchemy, Alembic, httpx, RapidFuzz, platformdirs, and ytmusicapi. Dev dependencies are pytest, pytest-asyncio, respx, ruff, and mypy. Frontend dependencies are React 19, React Router, TanStack Query, and TanStack Virtual; dev dependencies are TypeScript, Vite, Vitest, jsdom, Testing Library, ESLint, and Playwright. Generate and commit lock files. The ignore file must include:

~~~gitignore
.env
.env.*
!.env.example
oauth.json
browser.json
credentials*.json
*.sqlite
*.sqlite3
data/
.data/
backend/.venv/
backend/.pytest_cache/
backend/.mypy_cache/
backend/.ruff_cache/
frontend/node_modules/
frontend/dist/
frontend/coverage/
test-results/
playwright-report/
__pycache__/
*.py[cod]
~~~

- [ ] **Step 2: Write failing backend and frontend shell tests**

Create the environments and lock files with:

~~~powershell
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install -e "backend[dev]"
npm --prefix frontend install
~~~

~~~python
def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
~~~

~~~tsx
it("identifies the product and planning status", () => {
  render(<App />);
  expect(screen.getByRole("heading", { name: /playlist bridge/i })).toBeVisible();
});
~~~

- [ ] **Step 3: Run the shell tests and confirm failure**

Run python -m pytest backend/tests/api/test_health.py -q and npm --prefix frontend test -- --run src/App.test.tsx. Expected: import or assertion failures because the app shells do not exist yet.

- [ ] **Step 4: Implement the smallest running shells**

~~~python
from fastapi import FastAPI
from app.api.health import router as health_router

def create_app() -> FastAPI:
    app = FastAPI(title="Playlist Bridge", version="0.1.0")
    app.include_router(health_router, prefix="/api")
    return app

app = create_app()
~~~

Serve API routes before mounting the built frontend. backend/app/spa.py serves frontend/dist assets and returns index.html only for non-API navigation paths. Development uses Vite's /api proxy; the release command builds React and serves one loopback origin from FastAPI.

backend/tests/conftest.py creates TestClient(create_app()) with a temporary application-data path. frontend/src/test/setup.ts imports jest-dom matchers and restores mocks after each test.

~~~tsx
export function App() {
  return <main><h1>Playlist Bridge</h1><p>Local playlist transfer</p></main>;
}
~~~

- [ ] **Step 5: Run tests, lint, and builds**

Run npm test from the repository root, then npm run lint and npm run build. Expected: all commands pass and no generated artifact is tracked.

- [ ] **Step 6: Commit**

~~~bash
git add .gitignore .editorconfig README.md SECURITY.md CONTRIBUTING.md LICENSE package.json backend frontend
git commit -m "chore: establish public project foundation"
~~~

### Task 2: Domain State Machine and SQLite Schema

**Files:**
- Create: backend/app/domain/enums.py, backend/app/domain/models.py, backend/app/domain/state_machine.py
- Create: backend/app/persistence/db.py, backend/app/persistence/tables.py, backend/app/persistence/repositories.py
- Create: backend/alembic.ini, backend/migrations/env.py, backend/migrations/versions/0001_initial.py
- Test: backend/tests/domain/test_state_machine.py, backend/tests/persistence/test_repositories.py

**Interfaces:**
- Produces: JobStatus, MatchStatus, SupportStatus, TransferStatus, DestinationMode, Visibility
- Produces: ensure_transition(current: JobStatus, target: JobStatus) -> None
- Produces: Database.open(path: Path) and RepositorySet(session_factory)

- [ ] **Step 1: Write state-transition and duplicate-position tests**

~~~python
def test_review_must_finish_before_transfer():
    with pytest.raises(InvalidTransition):
        ensure_transition(JobStatus.AWAITING_REVIEW, JobStatus.TRANSFERRING)

def test_duplicate_track_ids_keep_distinct_positions(repos, job):
    repos.items.add(source_item(job.id, position=4, spotify_id="same"))
    repos.items.add(source_item(job.id, position=9, spotify_id="same"))
    assert [item.source_position for item in repos.items.list(job.id)] == [4, 9]
~~~

- [ ] **Step 2: Run tests and confirm they fail**

Run python -m pytest backend/tests/domain/test_state_machine.py backend/tests/persistence/test_repositories.py -q. Expected: missing domain and persistence modules.

- [ ] **Step 3: Implement enums, value objects, and legal transitions**

Define states exactly as the specification: draft, importing_source, matching, awaiting_review, ready_to_transfer, preparing_destination, transferring, completed, pausing, paused, cancelled, and failed. Use a mapping of allowed next states and raise InvalidTransition containing safe current and requested values.

~~~python
@dataclass(frozen=True)
class SourceItemValue:
    source_position: int
    spotify_id: str | None
    title: str
    artists: tuple[str, ...]
    album: str | None
    duration_ms: int | None
    isrc: str | None
    support_status: SupportStatus
    support_reason: str | None = None
~~~

- [ ] **Step 4: Implement SQLAlchemy tables and the initial migration**

Create transfer_jobs, source_items, match_candidates, append_batches, and job_events. Enforce unique(job_id, source_position), foreign keys, UUID text keys, integer revisions, and indexes for job status and item match status. Configure SQLite foreign keys and journal_mode=WAL on connect.

- [ ] **Step 5: Implement focused repositories**

Repositories must expose add/get/list/update methods and compare-and-swap job updates by revision. Do not return ORM rows outside persistence. Add a transaction that updates one item decision and all job counters atomically.

- [ ] **Step 6: Run migration and tests**

Run alembic -c backend/alembic.ini upgrade head against a temporary database, then run python -m pytest backend/tests/domain backend/tests/persistence -q. Expected: pass.

- [ ] **Step 7: Commit**

~~~bash
git add backend/app/domain backend/app/persistence backend/migrations backend/alembic.ini backend/tests/domain backend/tests/persistence
git commit -m "feat: add durable transfer domain"
~~~

### Task 3: Local Paths, Secret Safety, and Spotify PKCE

**Files:**
- Create: backend/app/settings/paths.py, backend/app/settings/secrets.py
- Create: backend/app/connectors/base.py, backend/app/connectors/spotify_auth.py
- Create: backend/app/api/errors.py, backend/app/api/setup.py
- Test: backend/tests/settings/test_secrets.py, backend/tests/connectors/test_spotify_auth.py, backend/tests/api/test_setup_spotify.py

**Interfaces:**
- Produces: AppPaths.from_platform() and AtomicSecretStore
- Produces: SpotifyAuth.begin(client_id: str) -> SpotifyAuthStart
- Produces: SpotifyAuth.complete(code: str, state: str) -> SpotifySession
- Produces: GET /api/setup and Spotify start/callback/disconnect endpoints

- [ ] **Step 1: Write tests for platform paths, redaction, and PKCE**

~~~python
def test_pkce_challenge_matches_verifier():
    verifier = "a" * 64
    assert pkce_challenge(verifier) == base64url_sha256(verifier)

def test_setup_response_never_contains_tokens(client, secret_store):
    secret_store.write("spotify_session", {"access_token": "secret", "refresh_token": "refresh"})
    body = client.get("/api/setup").json()
    assert "secret" not in json.dumps(body)
    assert "refresh" not in json.dumps(body)
~~~

Also assert callback state is single-use, expires, and rejects mismatches.

- [ ] **Step 2: Run the focused tests and confirm failure**

Run python -m pytest backend/tests/settings backend/tests/connectors/test_spotify_auth.py backend/tests/api/test_setup_spotify.py -q. Expected: missing implementations.

- [ ] **Step 3: Implement paths and atomic local secret storage**

Use platformdirs.user_data_path("PlaylistBridge", "PlaylistBridge"). Write credentials via a same-directory temporary file, flush and replace atomically, and request owner-only permissions where the platform supports them. API models expose only configured and connected booleans plus display names.

- [ ] **Step 4: Implement Spotify Authorization Code with PKCE**

Use redirect URI http://127.0.0.1:8765/api/setup/spotify/callback and scopes playlist-read-private user-read-private. Generate a cryptographically random verifier and state, persist them only until callback, exchange the code at accounts.spotify.com/api/token, and refresh before expiry. Never accept a caller-supplied redirect URI.

- [ ] **Step 5: Add stable setup endpoints and errors**

~~~python
@router.post("/spotify/start", response_model=SpotifyAuthStart)
def start_spotify(request: SpotifyClientId, auth: SpotifyAuthDep):
    return auth.begin(request.client_id)

@router.get("/spotify/callback")
def finish_spotify(code: str, state: str, auth: SpotifyAuthDep):
    auth.complete(code, state)
    return RedirectResponse(settings.frontend_setup_url)
~~~

The frontend setup URL is fixed by application mode: http://127.0.0.1:5173/setup for Vite development and http://127.0.0.1:8765/setup for the built app. Return errors as {"error": {"code": str, "message": str, "action": str | null, "field_errors": object | null}}.

- [ ] **Step 6: Run tests and a redaction scan**

Run python -m pytest backend/tests/settings backend/tests/connectors/test_spotify_auth.py backend/tests/api/test_setup_spotify.py -q, then rg -n "access_token|refresh_token|client_secret" backend/tests -g "*.json". Expected: tests pass and no recorded secret values appear.

- [ ] **Step 7: Commit**

~~~bash
git add backend/app/settings backend/app/connectors/base.py backend/app/connectors/spotify_auth.py backend/app/api backend/app/main.py backend/tests/settings backend/tests/connectors/test_spotify_auth.py backend/tests/api/test_setup_spotify.py
git commit -m "feat: add safe Spotify PKCE setup"
~~~

### Task 4: Spotify Inspection and Frozen Source Import

**Files:**
- Create: backend/app/connectors/spotify.py, backend/app/api/spotify.py
- Create: backend/app/transfer/service.py, backend/app/api/transfers.py
- Modify: backend/app/main.py
- Test: backend/tests/connectors/test_spotify.py, backend/tests/api/test_spotify.py, backend/tests/integration/test_source_import.py

**Interfaces:**
- Implements: SpotifyConnector protocol
- Produces: parse_spotify_playlist_id(value: str) -> str
- Produces: POST /api/spotify/inspect and POST /api/transfers
- Consumes: RepositorySet and connected SpotifySession

- [ ] **Step 1: Write URL, ownership, pagination, and resume tests**

Cover open.spotify.com/playlist/{id}, spotify:playlist:{id}, invalid hosts, a playlist owned by another user, a private playlist, a 101-item playlist over three 50-item pages, unavailable items, episodes, local files, repeated Spotify IDs, and restart from the first missing position.

~~~python
def test_import_preserves_duplicate_positions(service, spotify):
    spotify.items = [track("same"), track("x"), track("same")]
    job_id = service.import_source(create_request())
    items = service.items(job_id)
    assert [(x.source_position, x.spotify_id) for x in items] == [(0, "same"), (1, "x"), (2, "same")]
~~~

- [ ] **Step 2: Run tests and confirm failure**

Run python -m pytest backend/tests/connectors/test_spotify.py backend/tests/api/test_spotify.py backend/tests/integration/test_source_import.py -q. Expected: missing Spotify connector and routes.

- [ ] **Step 3: Implement the Spotify connector**

Use httpx with Authorization: Bearer from SpotifyAuth. GET /v1/me, /v1/playlists/{id}, and /v1/playlists/{id}/items with limit=50 and offset pagination. Map item, with track accepted as a compatibility alias, into SourceItemValue. Translate 401, 403, 404, 429, and 5xx responses into typed connector errors without response headers or bodies.

- [ ] **Step 4: Implement inspection and ownership validation**

POST /api/spotify/inspect accepts only url. Return playlist ID, name, owner display name, public flag, Spotify link, artwork link, and total. Require owner.id == current_user.id and public == true before returning an eligible preview.

- [ ] **Step 5: Implement resumable source import**

Create the job in draft, transition to importing_source, store every page in a short transaction, and update import_cursor. Before resuming an incomplete import, compare the playlist snapshot identifier; if changed, delete only that job's incomplete source rows and restart at zero with a warning event. Freeze a complete snapshot before transitioning to matching.

- [ ] **Step 6: Run connector and integration suites**

Run python -m pytest backend/tests/connectors/test_spotify.py backend/tests/api/test_spotify.py backend/tests/integration/test_source_import.py -q. Expected: pass with no live Spotify dependency.

- [ ] **Step 7: Commit**

~~~bash
git add backend/app/connectors/spotify.py backend/app/api/spotify.py backend/app/api/transfers.py backend/app/transfer/service.py backend/app/main.py backend/tests/connectors/test_spotify.py backend/tests/api/test_spotify.py backend/tests/integration/test_source_import.py
git commit -m "feat: import owned Spotify playlists"
~~~


### Task 5: Deterministic Matching Engine

**Files:**
- Create: backend/app/matching/normalize.py, backend/app/matching/queries.py, backend/app/matching/score.py
- Test: backend/tests/matching/test_normalize.py, backend/tests/matching/test_queries.py, backend/tests/matching/test_score.py
- Create: backend/tests/fixtures/matching_cases.json

**Interfaces:**
- Produces: normalize_track(title: str, artists: Sequence[str], album: str | None) -> NormalizedTrack
- Produces: build_queries(source: SourceItemValue) -> list[str]
- Produces: score_candidates(source: SourceItemValue, candidates: Sequence[YTMCandidate]) -> MatchResult

- [ ] **Step 1: Create explicit matching fixtures**

Include exact studio tracks, punctuation changes, reordered featured artists, diacritics, remaster-only differences, a source live version, an unwanted live candidate, acoustic, remix, cover, karaoke, sped-up, slowed, instrumental, duration boundaries at 2/5/10/20 seconds, a close runner-up, and no result.

~~~json
{
  "name": "reject_unrequested_live_version",
  "source": {"title": "Song", "artists": ["Artist"], "album": "Album", "duration_ms": 200000},
  "candidates": [
    {"video_id": "live", "title": "Song (Live)", "artists": ["Artist"], "duration_ms": 201000, "result_type": "song"}
  ],
  "expected": {"classification": "unmatched", "penalty": 25}
}
~~~

- [ ] **Step 2: Write failing normalization, query, and scoring tests**

Assert Unicode NFKC normalization, case folding, punctuation and whitespace normalization, feature-token equivalence, artist-set comparison, and separate version markers. Assert query order and video-ID deduplication. Assert score components total at most 100.

~~~python
def test_auto_accept_requires_margin(source, candidate_factory):
    result = score_candidates(source, [candidate_factory(score_shape="great"), candidate_factory(score_shape="close")])
    assert result.candidates[0].score >= 86
    assert result.classification is MatchStatus.REVIEW_REQUIRED
~~~

- [ ] **Step 3: Run tests and confirm failure**

Run python -m pytest backend/tests/matching -q. Expected: missing matching modules.

- [ ] **Step 4: Implement normalization and query construction**

Use unicodedata.normalize("NFKC", value).casefold(), normalize spacing and punctuation, and parse markers from a fixed vocabulary. Preserve a base-title value and a marker set. Return the four specification queries in stable order and remove duplicate query strings without reordering.

- [ ] **Step 5: Implement scoring and explanations**

Use RapidFuzz ratios for title, artists, and album. Award title 0–35, artists 0–30, duration 0–15, album 0–10, song type 0–5, and compatible markers 0–5. Apply the defined 25-point major-marker or 8-point remaster penalty. Clamp to 0–100 and persist the numeric breakdown and human-readable reason codes.

Classify >=86 with an >=8 runner-up margin as auto-accepted; treat no runner-up as margin 100. Classify >=65 or a top-two margin <8 as review-required. Otherwise classify unmatched.

- [ ] **Step 6: Run all matching fixtures and type checks**

Run python -m pytest backend/tests/matching -q and mypy backend/app/matching. Expected: pass with deterministic output over repeated runs.

- [ ] **Step 7: Commit**

~~~bash
git add backend/app/matching backend/tests/matching backend/tests/fixtures/matching_cases.json
git commit -m "feat: add explainable track matching"
~~~

### Task 6: YouTube Music OAuth and Isolated Connector

**Files:**
- Create: backend/app/connectors/ytmusic_auth.py, backend/app/connectors/ytmusic.py
- Modify: backend/app/api/setup.py
- Test: backend/tests/connectors/test_ytmusic_auth.py, backend/tests/connectors/test_ytmusic.py, backend/tests/api/test_setup_youtube.py

**Interfaces:**
- Produces: YouTubeMusicAuth.begin(client_id: str, client_secret: str) -> DeviceAuthChallenge
- Produces: YouTubeMusicAuth.poll(device_code: str) -> YouTubeAuthPoll
- Implements: YouTubeMusicConnector protocol
- Produces: YouTube start/poll/test/disconnect setup endpoints

- [ ] **Step 1: Write authentication and connector contract tests**

Test pending, slow_down, expired, denied, and successful device-code states; token refresh; redacted failures; Songs-filter search normalization; owned-playlist filtering; get_playlist(limit=None); public/private creation; and append with duplicates=True.

~~~python
def test_append_explicitly_preserves_duplicates(fake_ytmusic, connector):
    connector.append_video_ids("dest", ["a", "b", "a"])
    fake_ytmusic.add_playlist_items.assert_called_once_with(
        "dest", ["a", "b", "a"], duplicates=True
    )
~~~

- [ ] **Step 2: Run tests and confirm failure**

Run python -m pytest backend/tests/connectors/test_ytmusic_auth.py backend/tests/connectors/test_ytmusic.py backend/tests/api/test_setup_youtube.py -q. Expected: missing implementations.

- [ ] **Step 3: Implement Google device-code authentication**

Require a Google OAuth client of type TVs and Limited Input devices. Wrap ytmusicapi OAuthCredentials.get_code() and token_from_code(). Store device challenges temporarily, honor the provider interval, persist the resulting OAuth document atomically, and initialize YTMusic with OAuthCredentials. Do not return the device code or tokens to the frontend; return only user_code, verification_url, interval, and expiry.

- [ ] **Step 4: Implement the YouTube Music connector**

~~~python
def search_songs(self, query: str, limit: int = 5) -> list[YTMCandidate]:
    rows = self.client.search(query, filter="songs", limit=limit)
    return [map_song(row) for row in rows if row.get("videoId")]

def append_video_ids(self, playlist_id: str, video_ids: list[str]) -> None:
    self.client.add_playlist_items(playlist_id, video_ids, duplicates=True)
~~~

Map create visibility to PRIVATE or PUBLIC, request all owned playlists with get_library_playlists(limit=None), and retrieve complete destination content with get_playlist(playlist_id, limit=None). Never leak raw ytmusicapi responses above the connector.

- [ ] **Step 5: Add setup routes**

POST /api/setup/youtube/start accepts client_id and client_secret, POST /api/setup/youtube/poll accepts the opaque local challenge ID, POST /api/setup/youtube/test checks the authenticated account, and DELETE /api/setup/youtube removes only local credentials after confirmation.

- [ ] **Step 6: Run connector tests and dependency boundary check**

Run python -m pytest backend/tests/connectors/test_ytmusic_auth.py backend/tests/connectors/test_ytmusic.py backend/tests/api/test_setup_youtube.py -q, then rg -n "from ytmusicapi|import ytmusicapi" backend/app -g "*.py". Expected: tests pass and imports exist only in connectors/ytmusic_auth.py and connectors/ytmusic.py.

- [ ] **Step 7: Commit**

~~~bash
git add backend/app/connectors/ytmusic_auth.py backend/app/connectors/ytmusic.py backend/app/api/setup.py backend/tests/connectors backend/tests/api/test_setup_youtube.py
git commit -m "feat: isolate YouTube Music integration"
~~~

### Task 7: Retry Policy, Durable Worker, and Matching Progress

**Files:**
- Create: backend/app/transfer/retry.py, backend/app/transfer/worker.py
- Modify: backend/app/transfer/service.py, backend/app/main.py, backend/app/api/transfers.py
- Test: backend/tests/transfer/test_retry.py, backend/tests/transfer/test_worker.py, backend/tests/integration/test_matching_job.py, backend/tests/api/test_transfer_events.py

**Interfaces:**
- Produces: RetryPolicy.run(operation: Callable[[], T]) -> T
- Produces: TransferWorker.start(), wake(), stop(), and recover_abandoned_jobs()
- Produces: GET /api/transfers/{id}/events as text/event-stream
- Consumes: SpotifyConnector, YouTubeMusicConnector, score_candidates, RepositorySet

- [ ] **Step 1: Write retry and recovery tests with a fake clock**

Assert at most five attempts, exponential delays with bounded jitter, Retry-After support, no retry for authentication/validation/invariant errors, and redacted event messages. Interrupt matching after several items and assert resume begins at the first unfinished supported position.

~~~python
def test_browser_disconnect_does_not_stop_worker(worker, event_client, repos, job):
    stream = event_client(job.id)
    stream.close()
    worker.run_one_cycle()
    assert repos.jobs.get(job.id).match_cursor > 0
~~~

- [ ] **Step 2: Run tests and confirm failure**

Run python -m pytest backend/tests/transfer backend/tests/integration/test_matching_job.py backend/tests/api/test_transfer_events.py -q. Expected: missing worker and retry modules.

- [ ] **Step 3: Implement retry classification**

Retry typed rate-limit, network, and eligible server errors. Use delays min(max(base * 2 ** attempt, retry_after), max_delay) plus injected jitter. Store only stable error code, safe summary, attempt, and next-attempt time.

- [ ] **Step 4: Implement the single durable worker**

Use one backend-owned worker thread started and stopped by FastAPI lifespan. Poll runnable jobs, acquire one through a compare-and-swap revision update, perform one bounded unit, commit progress, and repeat. On startup, turn abandoned importing_source, matching, preparing_destination, or transferring jobs into paused recovery-required jobs.

- [ ] **Step 5: Implement the matching phase**

For each supported source position, issue deterministic queries serially with a randomized 500–900 ms spacing, collect at most five distinct candidates, score them, store candidates and classification atomically, and advance match_cursor. Move to awaiting_review if unresolved supported positions exist; otherwise move to ready_to_transfer.

- [ ] **Step 6: Add revision-safe commands and SSE**

POST /api/transfers/{id}/commands validates revision and command. SSE events contain job_id, revision, status, aggregate counts, and a safe last_event. Send a heartbeat every 15 seconds and close cleanly; the browser can reconnect using the latest revision.

- [ ] **Step 7: Run worker, integration, and existing suites**

Run python -m pytest backend/tests/transfer backend/tests/integration/test_matching_job.py backend/tests/api/test_transfer_events.py -q, then python -m pytest backend/tests -q. Expected: pass with fake connectors and fake time.

- [ ] **Step 8: Commit**

~~~bash
git add backend/app/transfer backend/app/main.py backend/app/api/transfers.py backend/tests/transfer backend/tests/integration/test_matching_job.py backend/tests/api/test_transfer_events.py
git commit -m "feat: run resumable matching jobs"
~~~

### Task 8: Review Queue and Decision API

**Files:**
- Modify: backend/app/transfer/service.py, backend/app/api/transfers.py, backend/app/persistence/repositories.py
- Test: backend/tests/api/test_review_items.py, backend/tests/integration/test_review_decisions.py

**Interfaces:**
- Produces: GET /api/transfers/{id}/items with status, query, cursor, and limit filters
- Produces: POST /api/transfers/{id}/items/{item_id}/search
- Produces: PUT /api/transfers/{id}/items/{item_id}/decision
- Consumes: YouTubeMusicConnector.search_songs and RepositorySet

- [ ] **Step 1: Write failing pagination and decision tests**

Test stable source-position ordering, cursor pagination, review/unmatched/unsupported/manual/skipped filters, custom query search, candidate acceptance, pasted YouTube URL validation, skip, counter updates, stale job revisions, and rejection of decisions after transfer starts.

~~~python
def test_every_supported_item_must_be_decided_before_transfer(service, job):
    service.decide(job.id, first.id, accept(first_candidate.id))
    with pytest.raises(UnresolvedItems):
        service.command(job.id, current_revision(job), JobCommand.BEGIN_TRANSFER)
~~~

- [ ] **Step 2: Run tests and confirm failure**

Run python -m pytest backend/tests/api/test_review_items.py backend/tests/integration/test_review_decisions.py -q. Expected: route and service failures.

- [ ] **Step 3: Implement paginated item reads**

Return source metadata, support state, selected result, up to five candidates, score explanation, and safe error. Use opaque cursors based on source position; limit defaults to 50 and is capped at 200. Never load all 2,500 candidates for one response.

- [ ] **Step 4: Implement custom search and pasted-link resolution**

Custom search uses the same connector throttling and candidate mapping but does not alter the decision until selection. Accept youtube.com/watch?v, youtu.be, and music.youtube.com/watch?v URLs, extract one video ID, fetch or search enough metadata to display it, and reject playlists or malformed IDs.

- [ ] **Step 5: Implement atomic decisions**

Accept candidate, accept pasted result, or skip in one transaction with job counters and revision. When no supported item remains unresolved, transition awaiting_review to ready_to_transfer. Editing a prior decision returns the job to awaiting_review until the aggregate check passes again.

- [ ] **Step 6: Run review and full backend suites**

Run python -m pytest backend/tests/api/test_review_items.py backend/tests/integration/test_review_decisions.py -q and python -m pytest backend/tests -q. Expected: pass.

- [ ] **Step 7: Commit**

~~~bash
git add backend/app/transfer/service.py backend/app/api/transfers.py backend/app/persistence/repositories.py backend/tests/api/test_review_items.py backend/tests/integration/test_review_decisions.py
git commit -m "feat: add uncertain match review API"
~~~

### Task 9: Destination Preparation, Ordered Append, and Reconciliation

**Files:**
- Create: backend/app/transfer/reconcile.py
- Modify: backend/app/transfer/worker.py, backend/app/transfer/service.py, backend/app/persistence/repositories.py
- Create: backend/app/api/youtube.py
- Modify: backend/app/api/transfers.py, backend/app/main.py
- Test: backend/tests/transfer/test_reconcile.py, backend/tests/integration/test_destination_transfer.py, backend/tests/api/test_destinations.py

**Interfaces:**
- Produces: reconcile_prefix(base_length: int, observed: Sequence[str], planned: Sequence[str]) -> int
- Produces: GET /api/youtube/playlists and destination fields on CreateJob
- Consumes: YouTubeMusicConnector destination methods and append_batches repository

- [ ] **Step 1: Write destination and crash-boundary tests**

Cover new private and public creation, existing-owned selection, rejection of non-owned destinations, exact order, duplicates=True, unsupported/skipped omission, 50-item batches, and capacity/provider failure. Simulate failure before send, after remote acceptance but before local confirmation, and after local confirmation.

~~~python
def test_reconcile_accepted_remote_batch_without_duplicate_write():
    planned = ["a", "b", "a", "c"]
    observed_tail = ["a", "b"]
    assert reconcile_prefix(7, observed_tail, planned) == 2

def test_divergent_tail_pauses():
    with pytest.raises(DestinationConflict):
        reconcile_prefix(7, ["a", "unexpected"], ["a", "b", "c"])
~~~

- [ ] **Step 2: Run tests and confirm failure**

Run python -m pytest backend/tests/transfer/test_reconcile.py backend/tests/integration/test_destination_transfer.py backend/tests/api/test_destinations.py -q. Expected: missing reconciliation and destination routes.

- [ ] **Step 3: Implement destination selection and preparation**

List only playlists with owned == true. For create mode, defer create_playlist until the job is ready and persist the returned ID immediately. For append mode, retrieve the complete destination, record destination_base_length, and create a fingerprint of the existing prefix for recovery diagnostics. Do not remove, replace, reorder, or deduplicate existing content.

- [ ] **Step 4: Build and persist the ordered write plan**

Select accepted source items ordered by source_position, exclude unsupported and skipped items, retain repeated video IDs, split into batches of 50, and store each ordered batch before any remote write. Fail the invariant if a supported item has no final decision.

- [ ] **Step 5: Implement write and uncertain-outcome recovery**

Mark a batch sending, call append_video_ids, then mark confirmed and advance write_cursor in one transaction. If the call outcome is uncertain or the process restarts, fetch destination video IDs from destination_base_length onward and compute the longest exact prefix. Confirm covered batches; resume from the first uncovered item. Pause with destination_conflict if the observed tail is not a prefix of the plan.

- [ ] **Step 6: Finish jobs and expose destination links**

Move preparing_destination to transferring to completed through legal transitions. Persist transferred and failed counts. A provider rejection pauses with a safe retry action; completion requires every planned batch confirmed.

- [ ] **Step 7: Run destination, integration, and backend suites**

Run python -m pytest backend/tests/transfer/test_reconcile.py backend/tests/integration/test_destination_transfer.py backend/tests/api/test_destinations.py -q, then python -m pytest backend/tests -q. Expected: pass.

- [ ] **Step 8: Commit**

~~~bash
git add backend/app/transfer backend/app/persistence/repositories.py backend/app/api/youtube.py backend/app/api/transfers.py backend/app/main.py backend/tests/transfer/test_reconcile.py backend/tests/integration/test_destination_transfer.py backend/tests/api/test_destinations.py
git commit -m "feat: transfer playlists with safe recovery"
~~~

### Task 10: History and Safe Report Exports

**Files:**
- Create: backend/app/reporting/export.py
- Modify: backend/app/api/transfers.py, backend/app/transfer/service.py
- Test: backend/tests/reporting/test_export.py, backend/tests/api/test_history.py

**Interfaces:**
- Produces: build_json_report(job_id: UUID) -> Iterator[bytes]
- Produces: build_csv_report(job_id: UUID) -> Iterator[bytes]
- Produces: GET /api/transfers, GET /api/transfers/{id}, and GET /api/transfers/{id}/exports/{format}

- [ ] **Step 1: Write report-completeness and disclosure tests**

Assert one exported row per source position, aggregate counts, source/destination metadata, score breakdown in JSON, flat score and error summaries in CSV, UTF-8 handling, formula-injection escaping for CSV cells beginning with =, +, -, or @, and absence of all seeded secret values.

~~~python
def test_csv_neutralizes_formula_cells(report):
    row = report.row(title="=HYPERLINK(\"bad\")")
    assert row["source_title"].startswith("'=")
~~~

- [ ] **Step 2: Run tests and confirm failure**

Run python -m pytest backend/tests/reporting/test_export.py backend/tests/api/test_history.py -q. Expected: missing reporting module and routes.

- [ ] **Step 3: Implement streaming JSON and CSV exports**

Query items in source order and stream output instead of loading the complete report into memory. Include source position, source metadata, support state, selected target metadata, confidence, decision origin, transfer result, and safe error. Use stable column names and schema_version=1.

- [ ] **Step 4: Implement history and job detail**

List jobs newest first with status and aggregate counts. Job detail returns destination link, current revision, legal commands, safe last event, and report availability. Cursor-paginate history with a default of 25 and cap of 100.

- [ ] **Step 5: Run reporting, API, and full backend suites**

Run python -m pytest backend/tests/reporting/test_export.py backend/tests/api/test_history.py -q and python -m pytest backend/tests -q. Expected: pass.

- [ ] **Step 6: Commit**

~~~bash
git add backend/app/reporting backend/app/api/transfers.py backend/app/transfer/service.py backend/tests/reporting backend/tests/api/test_history.py
git commit -m "feat: add transfer history and reports"
~~~

### Task 11: Typed React Shell, Setup, Source, and Destination

**Files:**
- Create: frontend/src/app/router.tsx, frontend/src/app/queryClient.ts
- Create: frontend/src/api/client.ts, frontend/src/api/types.ts, frontend/src/api/events.ts
- Create: frontend/src/components/AppShell.tsx, StatusBadge.tsx, ErrorNotice.tsx, ConfirmDialog.tsx
- Create: frontend/src/features/setup/SetupPage.tsx, useSetup.ts
- Create: frontend/src/features/source/SourcePage.tsx, useInspectPlaylist.ts
- Create: frontend/src/features/destination/DestinationPage.tsx, useDestinations.ts
- Create: frontend/src/styles/tokens.css, global.css
- Create: frontend/src/test/server.ts, render.tsx
- Test: colocated *.test.tsx files for each page and API client

**Interfaces:**
- Consumes: setup, Spotify inspect, YouTube playlists, transfer creation, and ApiError backend contracts
- Produces: routes /setup, /new/source, /new/destination, and /jobs/:jobId/*
- Produces: api.get<T>(), api.post<T>(), api.put<T>(), api.delete<T>()

- [ ] **Step 1: Define exact TypeScript API types and failing client tests**

~~~ts
export type ApiErrorBody = {
  error: {
    code: string;
    message: string;
    action: string | null;
    field_errors: Record<string, string> | null;
  };
};

export type JobSummary = {
  id: string;
  revision: number;
  status: JobStatus;
  source_name: string;
  counts: JobCounts;
};
~~~

Test JSON success, stable error parsing, network failure, and abort signals.

- [ ] **Step 2: Run frontend tests and confirm failure**

Run npm --prefix frontend test -- --run. Expected: missing router, client, and features.

- [ ] **Step 3: Implement the app shell and API/query layer**

Create an accessible skip link, header, main landmark, and status navigation. Configure TanStack Query with limited retries for GET requests and no implicit retry for mutations. The client must use relative /api URLs and never store credential responses in localStorage.

- [ ] **Step 4: Implement provider setup**

Spotify setup accepts a client ID, opens the returned authorization URL, and refreshes connection status after callback. YouTube setup accepts the Google TV client values, shows verification URL and user code, polls only at the backend-provided interval, and displays connected status without displaying tokens.

- [ ] **Step 5: Implement source inspection**

Provide one URL field with inline validation, loading state, and an eligible playlist preview showing name, owner, artwork, total, visibility, and Spotify attribution/link. Disable continuation if the backend reports non-owner or private.

- [ ] **Step 6: Implement destination selection**

Offer Create new and Append to existing. Create fields are name, description, and public/private with private selected initially. Append lists only owned playlists and clearly states that existing items remain untouched.

- [ ] **Step 7: Add accessible styling and run checks**

Use CSS custom-property tokens, visible focus, keyboard-operable dialogs, 44px primary controls, sufficient contrast, reduced-motion support, and responsive layouts from 768px upward. Run npm --prefix frontend test -- --run, npm --prefix frontend run lint, and npm --prefix frontend run build. Expected: pass.

- [ ] **Step 8: Commit**

~~~bash
git add frontend/src frontend/package.json frontend/package-lock.json frontend/vite.config.ts
git commit -m "feat: add setup and transfer creation UI"
~~~

### Task 12: Progress, Review, History, and Report UI

**Files:**
- Create: frontend/src/components/ProgressBar.tsx, DataTable.tsx, FilterBar.tsx, Pagination.tsx
- Create: frontend/src/features/progress/ProgressPage.tsx, useJobEvents.ts
- Create: frontend/src/features/review/ReviewPage.tsx, ReviewRow.tsx, CandidateList.tsx, useReviewItems.ts
- Create: frontend/src/features/history/HistoryPage.tsx
- Create: frontend/src/features/report/ReportPage.tsx
- Modify: frontend/src/app/router.tsx
- Test: colocated page/component tests and frontend/src/api/events.test.ts

**Interfaces:**
- Consumes: job detail, SSE, item pagination, search, decision, command, history, and export endpoints
- Produces: /jobs/:jobId/progress, /jobs/:jobId/review, /jobs/:jobId/report, and /history

- [ ] **Step 1: Write failing progress and SSE recovery tests**

Test live count updates, 15-second heartbeat tolerance, disconnect fallback to canonical GET, reconnect from last revision, pause/cancel commands, stale-revision refresh, and a browser reload that preserves backend work.

- [ ] **Step 2: Write failing large review-table tests**

Generate 2,500 logical rows and assert only the visible page or virtual window is mounted. Test status and text filters, keyboard navigation, candidate score explanations, custom search, pasted URL, accept, skip, safe bulk confirmation, and unresolved-count gating.

~~~tsx
expect(screen.getAllByRole("row").length).toBeLessThan(100);
await user.click(screen.getByRole("button", { name: /accept candidate/i }));
expect(server.lastDecision).toMatchObject({ kind: "candidate", revision: 12 });
~~~

- [ ] **Step 3: Run focused frontend tests and confirm failure**

Run npm --prefix frontend test -- --run src/features/progress src/features/review src/api/events.test.ts. Expected: missing features.

- [ ] **Step 4: Implement progress and commands**

Subscribe to SSE, merge only events with a newer revision, and invalidate the canonical job query after reconnect. Show status, completed/total, accepted/review/unmatched/skipped/failed counts, a non-clock progress estimate, and legal commands supplied by the API.

- [ ] **Step 5: Implement the review workflow**

Use server pagination capped at 200 or TanStack Virtual within a page. Show Spotify metadata beside candidates, marker warnings, component score explanation, and preview links. Require explicit confirmation for bulk acceptance and never include unmatched items in a bulk accept.

- [ ] **Step 6: Implement history and report**

History shows status, source, timestamps, counts, and legal resume/retry actions. Report shows the destination link, aggregate cards, safe warnings, and direct CSV/JSON download links. Do not load export bodies into browser memory.

- [ ] **Step 7: Run all frontend quality checks**

Run npm --prefix frontend test -- --run, npm --prefix frontend run lint, and npm --prefix frontend run build. Expected: pass with no accessibility violations asserted by component tests.

- [ ] **Step 8: Commit**

~~~bash
git add frontend/src
git commit -m "feat: add review and progress experience"
~~~

### Task 13: End-to-End Recovery, Public Documentation, and Release Gate

**Files:**
- Create: frontend/e2e/transfer.spec.ts, frontend/e2e/recovery.spec.ts
- Create: backend/tests/contract/test_live_spotify.py, backend/tests/contract/test_live_ytmusic.py
- Modify: README.md, SECURITY.md, CONTRIBUTING.md
- Create: docs/setup.md, docs/architecture.md, docs/test-playlist.md
- Create: scripts/check-secrets.ps1
- Modify: package.json

**Interfaces:**
- Consumes: complete backend and frontend application
- Produces: npm run verify and opt-in live connector checks

- [ ] **Step 1: Build a deterministic end-to-end fake-provider harness**

Seed a small playlist with exact, remaster, live, cover, duplicate, unavailable, and unmatched cases. Seed candidate responses and a destination service that can simulate an accepted remote batch followed by a local crash. Do not record real provider payloads.

- [ ] **Step 2: Write Playwright happy-path and recovery tests**

Test setup status, source preview, matching progress, uncertain review, pasted-link resolution, private create, existing append, exact final order, intentional duplicates, crash reconciliation, destination conflict, report downloads, and job-history reopening.

- [ ] **Step 3: Add opt-in live connector smoke tests**

Mark tests live and skip unless PLAYLIST_BRIDGE_LIVE_TESTS=1. Keep automated live checks read-only: validate both authenticated users, inspect the configured owned public Spotify test playlist, search one known YouTube Music song, and list owned destinations. Never create, mutate, delete, or print auth material in an automated smoke test; the controlled write acceptance remains a separate manual gate.

- [ ] **Step 4: Add a secret and artifact gate**

scripts/check-secrets.ps1 fails on tracked .env files, OAuth filenames, SQLite databases, access-token-shaped keys, client-secret values, private keys, or generated build directories. Allow only dummy names in .env.example and documentation. Also run git diff --check and verify no ignored runtime file is tracked.

~~~powershell
$tracked = git ls-files
$forbidden = $tracked | Select-String -Pattern '(^|/)(oauth|browser|credentials).*\.json$|\.sqlite3?$|(^|/)\.env$'
if ($forbidden) { throw "Sensitive or runtime files are tracked." }
~~~

- [ ] **Step 5: Finish public documentation**

README must state project status, capabilities, local-only security model, unofficial YouTube Music dependency, prerequisites, quick start, test commands, limitations, and links to setup and design docs. setup.md documents Spotify PKCE redirect registration and Google TV-device OAuth without example secrets. SECURITY.md instructs reporters to use GitHub private vulnerability reporting and tells users to revoke and rotate accidentally exposed provider credentials immediately.

- [ ] **Step 6: Run the complete release gate**

Run npm run verify. It must run backend tests with coverage, frontend tests, lint, type checks, production builds, Playwright fake-provider tests, the secret scan, and git diff --check. Then manually run the controlled small playlist acceptance described in docs/test-playlist.md before the 2,500-track job.

- [ ] **Step 7: Review tracked files before publication**

Run git status --short, git ls-files, and git grep -n -I -E "access_token|refresh_token|client_secret|BEGIN .*PRIVATE KEY". Inspect every match and confirm it is code, a dummy name, or security documentation—not a value. Confirm runtime data paths are outside the repository.

- [ ] **Step 8: Commit**

~~~bash
git add frontend/e2e backend/tests/contract README.md SECURITY.md CONTRIBUTING.md docs scripts package.json
git commit -m "test: complete public release gate"
~~~

## Execution Order and Review Gates

Execute Tasks 1–13 in order. Each task gets its own failing-test proof, implementation, passing focused suite, affected full suite, diff review, secret check, and commit. Stop after Task 6 for a live authentication checkpoint, after Task 9 for an interruption-recovery checkpoint, and after Task 13 for the controlled small-playlist acceptance. Do not begin the 2,500-track transfer until every release gate and the controlled acceptance playlist pass.

## Reference Documentation

- Product design: docs/superpowers/specs/2026-09-08-spotify-to-youtube-music-design.md
- Spotify PKCE: https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow
- Spotify playlist items: https://developer.spotify.com/documentation/web-api/reference/get-playlists-items
- ytmusicapi OAuth: https://ytmusicapi.readthedocs.io/en/stable/setup/oauth.html
- ytmusicapi playlists: https://ytmusicapi.readthedocs.io/en/stable/reference/playlists.html
- FastAPI testing: https://fastapi.tiangolo.com/tutorial/testing/
- React testing: https://testing-library.com/docs/react-testing-library/intro/
