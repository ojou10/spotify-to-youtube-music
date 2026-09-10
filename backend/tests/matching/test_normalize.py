from app.matching.normalize import normalize_text, normalize_track


def test_normalize_text_handles_unicode_case_punctuation_and_features():
    assert normalize_text("Beyoncé — Halo (feat. Jay-Z)") == "beyoncé halo and jay z"


def test_normalize_track_separates_version_markers_and_artist_order():
    track = normalize_track("Song (Live Remastered)", ["B", "A"], "Album")
    assert track.base_title == "song"
    assert track.artists == ("a", "b")
    assert track.markers == {"live", "remastered"}
