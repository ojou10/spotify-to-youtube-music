import os

import pytest


@pytest.mark.skipif(os.getenv("PLAYLIST_BRIDGE_LIVE_TESTS") != "1", reason="opt-in read-only provider contract test")
def test_live_spotify_is_opt_in():
    pytest.skip("Configure a disposable owned public test playlist before running live checks")
