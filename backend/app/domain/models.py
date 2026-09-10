from dataclasses import dataclass
from typing import NamedTuple

from app.domain.enums import MatchStatus, SupportStatus, Visibility


@dataclass(frozen=True)
class SpotifyUser:
    id: str
    display_name: str | None


@dataclass(frozen=True)
class PlaylistPreview:
    playlist_id: str
    name: str
    owner_id: str
    owner_name: str | None
    public: bool
    total: int
    spotify_url: str
    artwork_url: str | None
    snapshot_id: str | None


@dataclass(frozen=True)
class SourceItemValue:
    source_position: int
    spotify_id: str | None
    title: str
    artists: tuple[str, ...]
    album: str | None
    duration_ms: int | None
    isrc: str | None
    support_status: SupportStatus
    support_reason: str | None = None


@dataclass(frozen=True)
class YTMCandidate:
    video_id: str
    title: str
    artists: tuple[str, ...]
    album: str | None
    duration_ms: int | None
    result_type: str
    thumbnail_url: str | None = None
    url: str | None = None


@dataclass(frozen=True)
class ScoreBreakdown:
    title: float
    artists: float
    duration: float
    album: float
    result_type: float
    version: float
    penalties: tuple[str, ...] = ()
    penalty_points: float = 0.0

    @property
    def total(self) -> float:
        return max(
            0.0,
            min(100.0, self.title + self.artists + self.duration + self.album + self.result_type + self.version - self.penalty_points),
        )


@dataclass(frozen=True)
class ScoredCandidate:
    candidate: YTMCandidate
    score: float
    breakdown: ScoreBreakdown
    rank: int


class MatchResult(NamedTuple):
    classification: MatchStatus
    selected_video_id: str | None
    candidates: list[ScoredCandidate]


@dataclass(frozen=True)
class DestinationPlaylist:
    playlist_id: str
    title: str
    count: int
    owned: bool
    url: str | None = None


@dataclass(frozen=True)
class CreateJob:
    source_url: str
    destination_mode: str
    destination_playlist_id: str | None = None
    destination_name: str | None = None
    destination_description: str = ""
    destination_visibility: Visibility = Visibility.PRIVATE
