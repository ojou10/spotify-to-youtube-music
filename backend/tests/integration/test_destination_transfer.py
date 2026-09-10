from pathlib import Path

from app.domain.enums import JobStatus, MatchStatus, SupportStatus
from app.domain.models import DestinationPlaylist
from app.persistence.db import Database
from app.persistence.repositories import RepositorySet
from app.transfer.service import TransferService


class FakeYouTube:
    def __init__(self):
        self.appended = []

    def create_playlist(self, title, description, visibility):
        return DestinationPlaylist("dest", title, 0, True, "https://music.youtube.com/playlist?list=dest")

    def get_playlist(self, playlist_id, limit=None):
        return {"playlistId": playlist_id, "tracks": []}

    def append_video_ids(self, playlist_id, video_ids):
        self.appended.append((playlist_id, list(video_ids)))


def test_destination_transfer_preserves_order_duplicates_and_batches(tmp_path: Path):
    database = Database(tmp_path / "playlist.sqlite3")
    database.create_all()
    with database.session() as session:
        repos = RepositorySet(session)
        job = repos.jobs.add(status=JobStatus.READY_TO_TRANSFER.value, source_url="spotify:playlist:p", source_track_count=4, destination_mode="create", destination_name="Copy", destination_visibility="private")
        for position, video_id in enumerate(["a", "b", "a", "c"]):
            repos.items.add(job_id=job.id, source_position=position, spotify_id=str(position), title=str(position), artists=[], support_status=SupportStatus.SUPPORTED.value, match_status=MatchStatus.MANUAL_ACCEPTED.value, selected_video_id=video_id)
        job_id = job.id
    youtube = FakeYouTube()
    result = TransferService(database, spotify=None, youtube=youtube).transfer(job_id)
    assert result.status == JobStatus.COMPLETED.value
    assert youtube.appended == [("dest", ["a", "b", "a", "c"])]


def test_unsupported_and_skipped_positions_are_omitted(tmp_path: Path):
    database = Database(tmp_path / "playlist.sqlite3")
    database.create_all()
    with database.session() as session:
        repos = RepositorySet(session)
        job = repos.jobs.add(status=JobStatus.READY_TO_TRANSFER.value, source_url="spotify:playlist:p", source_track_count=2, destination_mode="create", destination_name="Copy", destination_visibility="private")
        repos.items.add(job_id=job.id, source_position=0, spotify_id="0", title="unsupported", artists=[], support_status=SupportStatus.UNSUPPORTED.value, match_status=MatchStatus.PENDING.value)
        repos.items.add(job_id=job.id, source_position=1, spotify_id="1", title="skipped", artists=[], support_status=SupportStatus.SUPPORTED.value, match_status=MatchStatus.SKIPPED.value, transfer_status="skipped")
        job_id = job.id
    youtube = FakeYouTube()
    result = TransferService(database, spotify=None, youtube=youtube).transfer(job_id)
    assert result.status == JobStatus.COMPLETED.value
    assert youtube.appended == []
