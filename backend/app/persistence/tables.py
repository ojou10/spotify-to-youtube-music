from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TransferJobRow(Base):
    __tablename__ = "transfer_jobs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    source_playlist_id: Mapped[str | None] = mapped_column(String(64))
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str | None] = mapped_column(Text)
    source_owner: Mapped[str | None] = mapped_column(Text)
    source_snapshot_marker: Mapped[str | None] = mapped_column(Text)
    source_track_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    supported_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    destination_mode: Mapped[str | None] = mapped_column(String(16))
    destination_playlist_id: Mapped[str | None] = mapped_column(String(128))
    destination_name: Mapped[str | None] = mapped_column(Text)
    destination_visibility: Mapped[str | None] = mapped_column(String(16))
    destination_base_length: Mapped[int | None] = mapped_column(Integer)
    import_cursor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    match_cursor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    write_cursor: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    counts: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    last_error_code: Mapped[str | None] = mapped_column(String(64))
    last_error_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class SourceItemRow(Base):
    __tablename__ = "source_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("transfer_jobs.id", ondelete="CASCADE"), nullable=False)
    source_position: Mapped[int] = mapped_column(Integer, nullable=False)
    spotify_id: Mapped[str | None] = mapped_column(String(128))
    title: Mapped[str] = mapped_column(Text, nullable=False)
    artists: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    album: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    isrc: Mapped[str | None] = mapped_column(String(32))
    support_status: Mapped[str] = mapped_column(String(24), nullable=False, default="supported")
    support_reason: Mapped[str | None] = mapped_column(Text)
    match_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    selected_video_id: Mapped[str | None] = mapped_column(String(32))
    selected_metadata: Mapped[dict | None] = mapped_column(JSON)
    transfer_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    error_summary: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint("job_id", "source_position", name="uq_source_job_position"),
        Index("ix_source_job_match", "job_id", "match_status"),
    )


class MatchCandidateRow(Base):
    __tablename__ = "match_candidates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    source_item_id: Mapped[str] = mapped_column(ForeignKey("source_items.id", ondelete="CASCADE"), nullable=False)
    video_id: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    artists: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    album: Mapped[str | None] = mapped_column(Text)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    result_type: Mapped[str] = mapped_column(String(32), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    score: Mapped[float] = mapped_column(nullable=False)
    score_breakdown: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    __table_args__ = (Index("ix_candidate_source_rank", "source_item_id", "rank"),)


class AppendBatchRow(Base):
    __tablename__ = "append_batches"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("transfer_jobs.id", ondelete="CASCADE"), nullable=False)
    batch_index: Mapped[int] = mapped_column(Integer, nullable=False)
    start_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    end_offset: Mapped[int] = mapped_column(Integer, nullable=False)
    video_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="planned")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("job_id", "batch_index", name="uq_batch_job_index"),)


class JobEventRow(Base):
    __tablename__ = "job_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    job_id: Mapped[str] = mapped_column(ForeignKey("transfer_jobs.id", ondelete="CASCADE"), nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    __table_args__ = (Index("ix_events_job_revision", "job_id", "revision"),)
