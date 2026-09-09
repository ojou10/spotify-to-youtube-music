from enum import StrEnum


class JobStatus(StrEnum):
    DRAFT = "draft"
    IMPORTING_SOURCE = "importing_source"
    MATCHING = "matching"
    AWAITING_REVIEW = "awaiting_review"
    READY_TO_TRANSFER = "ready_to_transfer"
    PREPARING_DESTINATION = "preparing_destination"
    TRANSFERRING = "transferring"
    COMPLETED = "completed"
    PAUSING = "pausing"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    FAILED = "failed"


class SupportStatus(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"


class MatchStatus(StrEnum):
    PENDING = "pending"
    AUTO_ACCEPTED = "auto_accepted"
    REVIEW_REQUIRED = "review_required"
    MANUAL_ACCEPTED = "manual_accepted"
    SKIPPED = "skipped"
    UNMATCHED = "unmatched"


class TransferStatus(StrEnum):
    PENDING = "pending"
    TRANSFERRED = "transferred"
    FAILED = "failed"
    SKIPPED = "skipped"


class DestinationMode(StrEnum):
    CREATE = "create"
    APPEND = "append"


class Visibility(StrEnum):
    PUBLIC = "public"
    PRIVATE = "private"
