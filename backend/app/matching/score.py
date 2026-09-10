from __future__ import annotations

from collections.abc import Sequence

from rapidfuzz.fuzz import ratio, token_set_ratio

from app.domain.enums import MatchStatus
from app.domain.models import (
    MatchResult,
    ScoreBreakdown,
    ScoredCandidate,
    SourceItemValue,
    YTMCandidate,
)
from app.matching.normalize import normalize_track

MAJOR_MARKERS = frozenset({"live", "acoustic", "remix", "cover", "karaoke", "sped_up", "slowed", "instrumental"})


def _duration_score(source: int | None, candidate: int | None) -> float:
    if source is None or candidate is None:
        return 0.0
    seconds = abs(source - candidate) / 1000
    if seconds <= 2:
        return 15.0
    if seconds <= 5:
        return 12.0
    if seconds <= 10:
        return 8.0
    if seconds <= 20:
        return 4.0
    return 0.0


def _version(source_markers: frozenset[str], candidate_markers: frozenset[str]) -> tuple[float, tuple[str, ...], float]:
    penalties: list[str] = []
    penalty_points = 0.0
    source_major = source_markers & MAJOR_MARKERS
    candidate_major = candidate_markers & MAJOR_MARKERS
    if candidate_major - source_major:
        penalties.append("candidate_has_unrequested_version")
        penalty_points += 25
    elif source_major - candidate_major:
        penalties.append("candidate_missing_requested_version")
        penalty_points += 25
    if ("remastered" in source_markers) != ("remastered" in candidate_markers):
        penalties.append("remaster_mismatch")
        penalty_points += 8
    compatible = 5.0 if source_markers == candidate_markers else 0.0
    if not source_markers and not candidate_markers:
        compatible = 5.0
    elif source_major == candidate_major and (source_markers ^ candidate_markers) <= {"remastered"}:
        compatible = 3.0
    return compatible, tuple(penalties), penalty_points


def _score(source: SourceItemValue, candidate: YTMCandidate) -> tuple[float, ScoreBreakdown]:
    source_normalized = normalize_track(source.title, source.artists, source.album)
    candidate_normalized = normalize_track(candidate.title, candidate.artists, candidate.album)
    title = ratio(source_normalized.base_title, candidate_normalized.base_title) / 100 * 35
    artists = token_set_ratio(" ".join(source_normalized.artists), " ".join(candidate_normalized.artists)) / 100 * 30
    album = ratio(source_normalized.album or "", candidate_normalized.album or "") / 100 * 10 if source_normalized.album and candidate_normalized.album else 0.0
    result_type = 5.0 if candidate.result_type == "song" else 2.0 if candidate.result_type in {"video", "music_video"} else 0.0
    version, penalties, penalty_points = _version(source_normalized.markers, candidate_normalized.markers)
    breakdown = ScoreBreakdown(title, artists, _duration_score(source.duration_ms, candidate.duration_ms), album, result_type, version, penalties, penalty_points)
    return breakdown.total, breakdown


def score_candidates(source: SourceItemValue, candidates: Sequence[YTMCandidate]) -> MatchResult:
    scored = [ScoredCandidate(candidate, *_score(source, candidate), rank=0) for candidate in candidates]
    scored.sort(key=lambda item: (-item.score, item.candidate.video_id))
    ranked = [ScoredCandidate(item.candidate, item.score, item.breakdown, rank) for rank, item in enumerate(scored, start=1)]
    if not ranked:
        return MatchResult(MatchStatus.UNMATCHED, None, [])
    top = ranked[0]
    margin = top.score - ranked[1].score if len(ranked) > 1 else 100.0
    if top.score >= 86 and margin >= 8:
        classification = MatchStatus.AUTO_ACCEPTED
        selected = top.candidate.video_id
    elif top.score >= 65:
        classification = MatchStatus.REVIEW_REQUIRED
        selected = None
    else:
        classification = MatchStatus.UNMATCHED
        selected = None
    return MatchResult(classification, selected, ranked)
