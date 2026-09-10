from pathlib import Path

import pytest

from app.connectors.base import ValidationFailure
from app.domain.enums import JobStatus, MatchStatus, SupportStatus
from app.persistence.db import Database
from app.persistence.repositories import RepositorySet
from app.persistence.tables import MatchCandidateRow
from app.transfer.service import TransferService


def setup_job(tmp_path: Path):
    database = Database(tmp_path / "playlist.sqlite3")
    database.create_all()
    with database.session() as session:
        repos = RepositorySet(session)
        job = repos.jobs.add(status=JobStatus.AWAITING_REVIEW.value, revision=3, source_url="spotify:playlist:p", source_track_count=2)
        first = repos.items.add(job_id=job.id, source_position=0, spotify_id="s0", title="Song", artists=["Artist"], support_status=SupportStatus.SUPPORTED.value, match_status=MatchStatus.REVIEW_REQUIRED.value)
        second = repos.items.add(job_id=job.id, source_position=1, spotify_id="s1", title="Other", artists=["Artist"], support_status=SupportStatus.SUPPORTED.value, match_status=MatchStatus.UNMATCHED.value)
        candidate = MatchCandidateRow(source_item_id=first.id, video_id="video", title="Song", artists=["Artist"], result_type="song", score=90, score_breakdown={}, rank=1)
        session.add(candidate)
        session.flush()
        return database, job.id, first.id, second.id, candidate.id


def test_decisions_are_atomic_and_require_current_revision(tmp_path: Path):
    database, job_id, first_id, second_id, candidate_id = setup_job(tmp_path)
    service = TransferService(database, spotify=None)
    with pytest.raises(ValidationFailure):
        service.decide(job_id, first_id, "accept_candidate", revision=2, candidate_id=candidate_id)
    job = service.decide(job_id, first_id, "accept_candidate", revision=3, candidate_id=candidate_id)
    assert job.status == JobStatus.AWAITING_REVIEW.value
    job = service.decide(job_id, second_id, "accept_url", revision=4, video_url="https://youtu.be/abcdefghijk")
    assert job.status == JobStatus.READY_TO_TRANSFER.value


def test_video_id_validation_and_paginated_item_reads(tmp_path: Path):
    database, job_id, first_id, _, _ = setup_job(tmp_path)
    service = TransferService(database, spotify=None)
    assert service.extract_video_id("https://music.youtube.com/watch?v=abcdefghijk") == "abcdefghijk"
    with pytest.raises(ValidationFailure):
        service.extract_video_id("https://youtube.com/playlist?list=abc")
    page = service.list_items(job_id, limit=1)
    assert len(page["items"]) == 1
    assert page["next_cursor"] == "0"
    assert service.list_items(job_id, cursor=page["next_cursor"], limit=1)["items"][0]["id"] != first_id
