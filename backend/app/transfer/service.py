from __future__ import annotations

from uuid import UUID

from app.connectors.base import ValidationFailure
from app.connectors.spotify import SpotifyConnector, SpotifyPlaylistPage, parse_spotify_playlist_id
from app.domain.enums import JobStatus
from app.domain.models import CreateJob
from app.persistence.db import Database
from app.persistence.repositories import RepositorySet


class TransferService:
    def __init__(self, database: Database, spotify: SpotifyConnector):
        self.database = database
        self.spotify = spotify
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
