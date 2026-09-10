from pathlib import Path

from app.domain.enums import JobStatus, SupportStatus
from app.domain.models import YTMCandidate
from app.persistence.db import Database
from app.persistence.repositories import RepositorySet
from app.transfer.worker import TransferWorker


class FakeYouTube:
    def search_songs(self, query, limit=5):
        return [YTMCandidate("video", "Song", ("Artist",), "Album", 200000, "song")]


def make_job(tmp_path: Path, status=JobStatus.MATCHING):
    database = Database(tmp_path / "playlist.sqlite3")
    database.create_all()
    with database.session() as session:
        repos = RepositorySet(session)
        job = repos.jobs.add(status=status.value, source_url="spotify:playlist:p", source_track_count=1, match_cursor=0)
        repos.items.add(job_id=job.id, source_position=0, spotify_id="s", title="Song", artists=["Artist"], album="Album", duration_ms=200000, support_status=SupportStatus.SUPPORTED.value)
        return database, job.id


def test_worker_matches_one_item_and_advances_job(tmp_path: Path):
    database, job_id = make_job(tmp_path)
    worker = TransferWorker(database, youtube=FakeYouTube(), sleep=lambda _: None, spacing=lambda: 0)
    assert worker.run_one_cycle()
    with database.session() as session:
        repos = RepositorySet(session)
        job = repos.jobs.get(job_id)
        row = repos.items.list(job_id)[0]
        assert job.status == JobStatus.READY_TO_TRANSFER.value
        assert job.match_cursor == 1
        assert row.selected_video_id == "video"


def test_worker_recovery_pauses_active_jobs(tmp_path: Path):
    database, job_id = make_job(tmp_path, JobStatus.MATCHING)
    worker = TransferWorker(database, youtube=FakeYouTube())
    worker.recover_abandoned_jobs()
    with database.session() as session:
        job = RepositorySet(session).jobs.get(job_id)
        assert job.status == JobStatus.PAUSED.value
        assert job.last_error_code == "recovery_required"
