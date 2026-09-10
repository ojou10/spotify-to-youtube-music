from __future__ import annotations

import re
from uuid import UUID

from sqlalchemy import select

from app.connectors.base import ValidationFailure
from app.connectors.spotify import SpotifyConnector, SpotifyPlaylistPage, parse_spotify_playlist_id
from app.domain.enums import JobStatus, SupportStatus
from app.domain.models import CreateJob
from app.persistence.db import Database
from app.persistence.repositories import RepositorySet
from app.persistence.tables import MatchCandidateRow, SourceItemRow

VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")


class TransferService:
    def __init__(self, database: Database, spotify: SpotifyConnector, youtube=None):
        self.database = database
        self.spotify = spotify
        self.youtube = youtube
        self.database.create_all()

    def inspect(self, source_url: str):
        playlist_id = parse_spotify_playlist_id(source_url)
        preview = self.spotify.playlist_preview(playlist_id)
        user = self.spotify.current_user()
        if not preview.public:
            raise ValidationFailure("The Spotify playlist must be public")
        if preview.owner_id != user.id:
            raise ValidationFailure("Only playlists owned by the connected Spotify account can be imported")
        return preview

    def import_source(self, request: CreateJob | dict):
        if isinstance(request, dict):
            request = CreateJob(**request)
        preview = self.inspect(request.source_url)
        with self.database.session() as session:
            repos = RepositorySet(session)
            job = repos.jobs.add(
                status=JobStatus.DRAFT.value, source_playlist_id=preview.playlist_id, source_url=request.source_url,
                source_name=preview.name, source_owner=preview.owner_name, source_snapshot_marker=preview.snapshot_id,
                source_track_count=preview.total, destination_mode=request.destination_mode,
                destination_playlist_id=request.destination_playlist_id, destination_name=request.destination_name,
                destination_visibility=request.destination_visibility.value if hasattr(request.destination_visibility, "value") else request.destination_visibility,
            )
            job_id = job.id
        return self.resume_source(job_id)

    def resume_source(self, job_id: UUID | str):
        with self.database.session() as session:
            repos = RepositorySet(session)
            job = repos.jobs.get(job_id)
            if job is None:
                raise ValidationFailure("Transfer job not found")
            preview = self.inspect(job.source_url)
            if job.source_snapshot_marker and preview.snapshot_id and job.source_snapshot_marker != preview.snapshot_id:
                repos.items.delete_for_job(job.id)
                repos.events.add(job.id, job.revision, "source_snapshot_changed", {"previous": job.source_snapshot_marker, "current": preview.snapshot_id})
                job = repos.jobs.update(job.id, source_snapshot_marker=preview.snapshot_id, import_cursor=0, source_track_count=preview.total)
            if job.status == JobStatus.DRAFT.value:
                job = repos.jobs.transition(job.id, job.revision, JobStatus.IMPORTING_SOURCE)
            offset = job.import_cursor
            total = preview.total
            while offset < total:
                if hasattr(self.spotify, "page"):
                    page = self.spotify.page(preview.playlist_id, offset)
                else:
                    values = tuple(getattr(self.spotify, "items", ())[offset : offset + 50])
                    page = SpotifyPlaylistPage(values, total, offset + len(values) if values else None, preview.snapshot_id)
                for item in page.items:
                    repos.items.add(job_id=job.id, source_position=item.source_position, spotify_id=item.spotify_id, title=item.title, artists=list(item.artists), album=item.album, duration_ms=item.duration_ms, isrc=item.isrc, support_status=item.support_status.value, support_reason=item.support_reason)
                offset += len(page.items)
                rows = repos.items.list(job.id)
                repos.jobs.update(job.id, import_cursor=offset, supported_count=sum(1 for item in rows if item.support_status == "supported"))
                if not page.items:
                    break
            job = repos.jobs.get(job.id)
            if job and job.import_cursor >= total:
                job = repos.jobs.transition(job.id, job.revision, JobStatus.MATCHING)
            return job

    def items(self, job_id: UUID | str):
        with self.database.session() as session:
            return RepositorySet(session).items.list(job_id)

    def list_items(self, job_id: UUID | str, *, status: str | None = None, query: str | None = None, cursor: str | None = None, limit: int = 50) -> dict:
        limit = max(1, min(200, limit))
        with self.database.session() as session:
            statement = select(SourceItemRow).where(SourceItemRow.job_id == str(job_id)).order_by(SourceItemRow.source_position)
            if status:
                statement = statement.where(SourceItemRow.match_status == status)
            if query:
                statement = statement.where(SourceItemRow.title.ilike(f"%{query}%"))
            if cursor:
                statement = statement.where(SourceItemRow.source_position > int(cursor))
            rows = list(session.scalars(statement.limit(limit + 1)))
            has_more = len(rows) > limit
            rows = rows[:limit]
            candidates = {row.id: list(session.scalars(select(MatchCandidateRow).where(MatchCandidateRow.source_item_id == row.id).order_by(MatchCandidateRow.rank))) for row in rows}
            return {"items": [self._item_payload(row, candidates[row.id]) for row in rows], "next_cursor": str(rows[-1].source_position) if has_more and rows else None}

    @staticmethod
    def _item_payload(row: SourceItemRow, candidates: list[MatchCandidateRow]) -> dict:
        return {"id": row.id, "source_position": row.source_position, "spotify_id": row.spotify_id, "title": row.title, "artists": row.artists, "album": row.album, "duration_ms": row.duration_ms, "support_status": row.support_status, "support_reason": row.support_reason, "match_status": row.match_status, "selected_video_id": row.selected_video_id, "error_summary": row.error_summary, "candidates": [{"id": candidate.id, "video_id": candidate.video_id, "title": candidate.title, "artists": candidate.artists, "album": candidate.album, "duration_ms": candidate.duration_ms, "score": candidate.score, "score_breakdown": candidate.score_breakdown, "rank": candidate.rank, "url": candidate.url} for candidate in candidates]}

    def decide(self, job_id: UUID | str, item_id: str, action: str, *, revision: int | None = None, candidate_id: str | None = None, video_url: str | None = None):
        with self.database.session() as session:
            repos = RepositorySet(session)
            job = repos.jobs.get(job_id)
            row = repos.items.get(item_id)
            if not job or not row or row.job_id != str(job_id):
                raise ValidationFailure("Transfer item not found")
            if revision is not None and revision != job.revision:
                raise ValidationFailure("The transfer changed; refresh before deciding")
            if job.status in {JobStatus.TRANSFERRING.value, JobStatus.COMPLETED.value}:
                raise ValidationFailure("Decisions are closed after transfer begins")
            if action == "skip":
                row.match_status = "skipped"
                row.selected_video_id = None
                row.transfer_status = "skipped"
            elif action == "accept_candidate":
                candidate = session.get(MatchCandidateRow, candidate_id) if candidate_id else None
                if not candidate or candidate.source_item_id != row.id:
                    raise ValidationFailure("Candidate not found for this item")
                row.match_status = "manual_accepted"
                row.selected_video_id = candidate.video_id
            elif action == "accept_url":
                video_id = self.extract_video_id(video_url or "")
                row.match_status = "manual_accepted"
                row.selected_video_id = video_id
            else:
                raise ValidationFailure("Unknown review decision")
            job = repos.jobs.update(job.id, revision=job.revision + 1)
            supported = repos.items.list(job.id)
            unresolved = any(item.support_status == SupportStatus.SUPPORTED.value and item.match_status in {"pending", "review_required", "unmatched"} for item in supported)
            if job.status == JobStatus.AWAITING_REVIEW.value and not unresolved:
                job = repos.jobs.transition(job.id, job.revision, JobStatus.READY_TO_TRANSFER)
            return job

    def search_item(self, item_id: str, query: str):
        return self.youtube.search_songs(query, limit=5)

    @staticmethod
    def extract_video_id(value: str) -> str:
        value = value.strip()
        if VIDEO_ID_PATTERN.fullmatch(value):
            return value
        match = re.match(r"^https://(?:(?:www\.)?youtube\.com/watch\?v=|music\.youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})(?:[&#?].*)?$", value)
        if not match:
            raise ValidationFailure("Enter a single YouTube Music video link")
        return match.group(1)
