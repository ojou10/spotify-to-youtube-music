import os

import pytest


@pytest.mark.skipif(os.getenv("PLAYLIST_BRIDGE_LIVE_TESTS") != "1", reason="opt-in read-only provider contract test")
def test_live_ytmusic_is_opt_in():
    pytest.skip("Configure local read-only YouTube Music credentials before running live checks")
