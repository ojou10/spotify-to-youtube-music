from app.domain.enums import MatchStatus, SupportStatus
from app.domain.models import SourceItemValue, YTMCandidate
from app.matching.score import score_candidates


def source(title="Song", artists=("Artist",), album="Album", duration=200000):
    return SourceItemValue(0, "id", title, artists, album, duration, None, SupportStatus.SUPPORTED)


def candidate(video_id="v", title="Song", artists=("Artist",), album="Album", duration=200000, result_type="song"):
    return YTMCandidate(video_id, title, artists, album, duration, result_type)


def test_exact_match_auto_accepts_with_no_runner_up():
    result = score_candidates(source(), [candidate()])
    assert result.classification is MatchStatus.AUTO_ACCEPTED
    assert result.selected_video_id == "v"
    assert result.candidates[0].score >= 86


def test_unrequested_live_version_is_not_auto_accepted():
    result = score_candidates(source(), [candidate(video_id="live", title="Song (Live)", duration=201000)])
    assert result.classification is MatchStatus.REVIEW_REQUIRED
    assert "candidate_has_unrequested_version" in result.candidates[0].breakdown.penalties
    assert result.candidates[0].score < 86


def test_close_runner_up_requires_review():
    result = score_candidates(source(), [candidate(video_id="a"), candidate(video_id="b", title="Song!" )])
    assert result.classification is MatchStatus.REVIEW_REQUIRED
