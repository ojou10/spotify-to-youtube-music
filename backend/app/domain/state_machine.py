from app.domain.enums import JobStatus


class InvalidTransition(ValueError):
    def __init__(self, current: JobStatus, target: JobStatus):
        super().__init__(f"invalid job transition: {current.value} -> {target.value}")
        self.current = current
        self.target = target


_ACTIVE = {
    JobStatus.IMPORTING_SOURCE,
    JobStatus.MATCHING,
    JobStatus.AWAITING_REVIEW,
    JobStatus.READY_TO_TRANSFER,
    JobStatus.PREPARING_DESTINATION,
    JobStatus.TRANSFERRING,
}

_ALLOWED: dict[JobStatus, set[JobStatus]] = {
    JobStatus.DRAFT: {JobStatus.IMPORTING_SOURCE, JobStatus.CANCELLED},
    JobStatus.IMPORTING_SOURCE: {JobStatus.MATCHING, JobStatus.PAUSING, JobStatus.PAUSED, JobStatus.FAILED},
    JobStatus.MATCHING: {JobStatus.AWAITING_REVIEW, JobStatus.READY_TO_TRANSFER, JobStatus.PAUSING, JobStatus.PAUSED, JobStatus.FAILED},
    JobStatus.AWAITING_REVIEW: {JobStatus.MATCHING, JobStatus.READY_TO_TRANSFER, JobStatus.PAUSING, JobStatus.PAUSED, JobStatus.CANCELLED},
    JobStatus.READY_TO_TRANSFER: {JobStatus.PREPARING_DESTINATION, JobStatus.PAUSING, JobStatus.PAUSED, JobStatus.CANCELLED},
    JobStatus.PREPARING_DESTINATION: {JobStatus.TRANSFERRING, JobStatus.PAUSING, JobStatus.PAUSED, JobStatus.FAILED},
    JobStatus.TRANSFERRING: {JobStatus.COMPLETED, JobStatus.PAUSING, JobStatus.PAUSED, JobStatus.FAILED},
    JobStatus.PAUSING: {JobStatus.PAUSED},
    JobStatus.PAUSED: _ACTIVE | {JobStatus.CANCELLED, JobStatus.FAILED},
    JobStatus.COMPLETED: set(),
    JobStatus.CANCELLED: set(),
    JobStatus.FAILED: set(),
}


def ensure_transition(current: JobStatus, target: JobStatus) -> None:
    if target not in _ALLOWED[current]:
        raise InvalidTransition(current, target)
