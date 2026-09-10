from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.domain.enums import JobStatus
from app.persistence.tables import JobEventRow, SourceItemRow, TransferJobRow


class JobRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, **values) -> TransferJobRow:
        row = TransferJobRow(**values)
        self.session.add(row)
        self.session.flush()
        return row

    def get(self, job_id: UUID | str) -> TransferJobRow | None:
        return self.session.get(TransferJobRow, str(job_id))

    def transition(self, job_id: UUID | str, revision: int, status: JobStatus) -> TransferJobRow:
        result = self.session.execute(
            update(TransferJobRow)
            .where(TransferJobRow.id == str(job_id), TransferJobRow.revision == revision)
            .values(status=status.value, revision=revision + 1)
        )
        if result.rowcount != 1:
            raise ValueError("stale job revision")
        self.session.flush()
        return self.get(job_id)

    def update(self, job_id: UUID | str, **values) -> TransferJobRow:
        self.session.execute(update(TransferJobRow).where(TransferJobRow.id == str(job_id)).values(**values))
        self.session.flush()
        return self.get(job_id)

    def list_status(self, statuses: set[JobStatus]) -> list[TransferJobRow]:
        return list(self.session.scalars(select(TransferJobRow).where(TransferJobRow.status.in_([status.value for status in statuses])).order_by(TransferJobRow.created_at)))


class SourceItemRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, **values) -> SourceItemRow:
        row = SourceItemRow(**values)
        self.session.add(row)
        self.session.flush()
        return row

    def list(self, job_id: UUID | str) -> list[SourceItemRow]:
        return list(
            self.session.scalars(
                select(SourceItemRow)
                .where(SourceItemRow.job_id == str(job_id))
                .order_by(SourceItemRow.source_position)
            )
        )

    def delete_for_job(self, job_id: UUID | str) -> None:
        self.session.execute(delete(SourceItemRow).where(SourceItemRow.job_id == str(job_id)))
        self.session.flush()

    def get(self, item_id: str) -> SourceItemRow | None:
        return self.session.get(SourceItemRow, item_id)


class EventRepository:
    def __init__(self, session: Session):
        self.session = session

    def add(self, job_id: UUID | str, revision: int, event_type: str, payload: dict) -> JobEventRow:
        row = JobEventRow(job_id=str(job_id), revision=revision, event_type=event_type, payload=payload)
        self.session.add(row)
        self.session.flush()
        return row


class RepositorySet:
    def __init__(self, session: Session):
        self.jobs = JobRepository(session)
        self.items = SourceItemRepository(session)
        self.events = EventRepository(session)
