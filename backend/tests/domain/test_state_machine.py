import pytest

from app.domain.enums import JobStatus
from app.domain.state_machine import InvalidTransition, ensure_transition


def test_review_must_finish_before_transfer():
    with pytest.raises(InvalidTransition):
        ensure_transition(JobStatus.AWAITING_REVIEW, JobStatus.TRANSFERRING)


def test_review_can_return_to_matching():
    ensure_transition(JobStatus.AWAITING_REVIEW, JobStatus.MATCHING)


def test_paused_can_resume_any_active_state():
    ensure_transition(JobStatus.PAUSED, JobStatus.MATCHING)
