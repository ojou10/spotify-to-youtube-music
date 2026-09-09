from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError

from app.domain.enums import JobStatus
from app.persistence.db import Database
from app.persistence.tables import Base


@pytest.fixture
def database(tmp_path: Path):
    db = Database(tmp_path / "test.sqlite3")
    Base.metadata.create_all(db.engine)
    return db


def test_duplicate_source_positions_are_rejected(database):
    from app.persistence.repositories import RepositorySet

    with database.session() as session:
        repos = RepositorySet(session)
        job = repos.jobs.add(source_url="spotify:playlist:abc", status=JobStatus.DRAFT.value)
        repos.items.add(job_id=job.id, source_position=0, title="A", artists=["Artist"])
        with pytest.raises(IntegrityError):
            repos.items.add(job_id=job.id, source_position=0, title="B", artists=["Artist"])
        session.rollback()


def test_job_transition_uses_compare_and_swap(database):
    from app.persistence.repositories import RepositorySet

    with database.session() as session:
        repos = RepositorySet(session)
        job = repos.jobs.add(source_url="spotify:playlist:abc", status=JobStatus.DRAFT.value)
        moved = repos.jobs.transition(job.id, 0, JobStatus.IMPORTING_SOURCE)
        assert moved.status == JobStatus.IMPORTING_SOURCE.value
        with pytest.raises(ValueError, match="stale"):
            repos.jobs.transition(job.id, 0, JobStatus.MATCHING)
