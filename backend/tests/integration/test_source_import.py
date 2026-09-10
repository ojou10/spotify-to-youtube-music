from pathlib import Path

from sqlalchemy import delete

from app.connectors.spotify import SpotifyPlaylistPage
from app.domain.enums import DestinationMode, SupportStatus, Visibility
from app.domain.models import CreateJob, PlaylistPreview, SourceItemValue, SpotifyUser
from app.persistence.db import Database
from app.transfer.service import TransferService


class FakeSpotify:
    def __init__(self, items):
        self.items = items
        self.preview = PlaylistPreview("playlist", "My playlist", "me", "Me", True, len(items), "https://open.spotify.com/playlist/playlist", None, "snapshot")

    def playlist_preview(self, playlist_id):
        return self.preview

    def current_user(self):
        return SpotifyUser("me", "Me")

    def page(self, playlist_id, offset=0, limit=50):
        values = tuple(self.items[offset : offset + limit])
        next_offset = offset + len(values) if values and offset + len(values) < len(self.items) else None
        return SpotifyPlaylistPage(values, len(self.items), next_offset, self.preview.snapshot_id)


def item(position, spotify_id):
    return SourceItemValue(position, spotify_id, f"Song {spotify_id}", ("Artist",), "Album", 1000, None, SupportStatus.SUPPORTED)


def test_import_preserves_duplicate_positions(tmp_path: Path):
    source = [item(0, "same"), item(1, "x"), item(2, "same")]
    service = TransferService(Database(tmp_path / "playlist.sqlite3"), FakeSpotify(source))
    job = service.import_source(CreateJob("https://open.spotify.com/playlist/playlist", DestinationMode.CREATE, destination_name="YouTube copy", destination_visibility=Visibility.PRIVATE))
    rows = service.items(job.id)
    assert [(row.source_position, row.spotify_id) for row in rows] == [(0, "same"), (1, "x"), (2, "same")]
    assert job.status == "matching"
    assert job.import_cursor == 3


def test_resume_starts_at_first_missing_position(tmp_path: Path):
    source = [item(i, str(i)) for i in range(3)]
    fake = FakeSpotify(source)
    database = Database(tmp_path / "playlist.sqlite3")
    service = TransferService(database, fake)
    job = service.import_source(CreateJob("https://open.spotify.com/playlist/playlist", DestinationMode.CREATE))
    with database.session() as session:
        from app.persistence.repositories import RepositorySet
        from app.persistence.tables import SourceItemRow
        session.execute(delete(SourceItemRow).where(SourceItemRow.job_id == job.id, SourceItemRow.source_position > 0))
        RepositorySet(session).jobs.update(job.id, status="importing_source", revision=job.revision, import_cursor=1)
    resumed = service.resume_source(job.id)
    assert resumed.import_cursor == 3
    assert len(service.items(job.id)) == 3
