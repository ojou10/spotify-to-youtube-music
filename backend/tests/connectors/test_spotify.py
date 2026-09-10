import httpx
import pytest
import respx

from app.connectors.base import ConnectorError, ValidationFailure
from app.connectors.spotify import SpotifyConnector, parse_spotify_playlist_id
from app.domain.enums import SupportStatus


def test_parse_spotify_playlist_id_accepts_supported_forms():
    assert parse_spotify_playlist_id("https://open.spotify.com/playlist/abc_123?si=x") == "abc_123"
    assert parse_spotify_playlist_id("spotify:playlist:abc_123") == "abc_123"


def test_parse_spotify_playlist_id_rejects_other_hosts():
    with pytest.raises(ValidationFailure):
        parse_spotify_playlist_id("https://example.com/playlist/abc")


class Auth:
    def access_token(self):
        return "access"


@respx.mock
def test_playlist_items_paginate_and_preserve_positions():
    first = [{"track": {"type": "track", "id": f"id-{i}", "name": f"Song {i}", "artists": [{"name": "Artist"}], "album": {"name": "Album"}, "duration_ms": 1000}} for i in range(50)]
    second = [{"track": {"type": "track", "id": f"id-{i}", "name": f"Song {i}", "artists": [{"name": "Artist"}], "album": {"name": "Album"}, "duration_ms": 1000}} for i in range(50, 101)]
    respx.get("https://api.spotify.com/v1/playlists/p/items").mock(side_effect=[httpx.Response(200, json={"items": first, "total": 101, "next": "next"}), httpx.Response(200, json={"items": second, "total": 101, "next": None})])
    connector = SpotifyConnector(Auth())
    items = list(connector.iter_items("p"))
    assert [item.source_position for item in items] == list(range(101))
    assert items[-1].spotify_id == "id-100"


def test_map_item_marks_episodes_and_local_files_unsupported():
    episode = SpotifyConnector._map_item({"track": {"type": "episode", "id": "ep", "name": "Talk"}}, 2)
    local = SpotifyConnector._map_item({"track": {"type": "track", "name": "Local", "is_local": True}}, 3)
    assert episode.support_status == SupportStatus.UNSUPPORTED
    assert episode.support_reason == "episode"
    assert local.support_reason == "local_file"


@respx.mock
def test_status_errors_are_typed_without_provider_payload():
    respx.get("https://api.spotify.com/v1/me").mock(return_value=httpx.Response(429, json={"secret": "do-not-leak"}, headers={"Retry-After": "10"}))
    with pytest.raises(ConnectorError) as error:
        SpotifyConnector(Auth()).current_user()
    assert error.value.code == "spotify_rate_limited"
    assert "secret" not in str(error.value)
