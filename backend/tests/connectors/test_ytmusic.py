from pathlib import Path

from app.connectors.ytmusic import YouTubeMusicConnector
from app.connectors.ytmusic_auth import YouTubeMusicAuth
from app.domain.enums import Visibility
from app.settings.secrets import AtomicSecretStore


class FakeClient:
    def __init__(self):
        self.calls = []

    def search(self, *args, **kwargs):
        self.calls.append(("search", args, kwargs))
        return [{"videoId": "v", "title": "Song", "artists": [{"name": "Artist"}], "album": {"name": "Album"}, "duration_seconds": 200, "resultType": "song", "thumbnails": [{"url": "https://img"}]}]

    def get_library_playlists(self, **kwargs):
        self.calls.append(("library", kwargs))
        return [{"playlistId": "p", "title": "Playlist", "count": 2}]

    def get_playlist(self, *args, **kwargs):
        self.calls.append(("playlist", args, kwargs))
        return {"playlistId": args[0], "tracks": []}

    def create_playlist(self, *args):
        self.calls.append(("create", args))
        return "new"

    def add_playlist_items(self, *args, **kwargs):
        self.calls.append(("append", args, kwargs))


class Auth:
    def session(self):
        return {"client_id": "id", "client_secret": "secret", "refresh_token": "refresh", "access_token": "access"}


def make_connector(tmp_path: Path):
    client = FakeClient()
    return YouTubeMusicConnector(YouTubeMusicAuth(AtomicSecretStore(tmp_path / "secrets.json")), client=client), client


def test_search_uses_songs_filter_and_maps_metadata(tmp_path: Path):
    connector = YouTubeMusicConnector(Auth(), client=FakeClient())
    result = connector.search_songs("Song Artist")
    assert result[0].duration_ms == 200000
    assert connector._client().calls[0][2] == {"filter": "songs", "limit": 5}


def test_playlist_operations_preserve_limits_visibility_and_duplicates(tmp_path: Path):
    connector, client = make_connector(tmp_path)
    assert connector.list_owned_playlists()[0].owned
    connector.get_playlist("p")
    connector.create_playlist("New", "Description", Visibility.PUBLIC)
    connector.append_video_ids("p", ["a", "b", "a"])
    assert ("library", {"limit": None}) in client.calls
    assert ("playlist", ("p",), {"limit": None}) in client.calls
    assert ("append", ("p", ["a", "b", "a"]), {"duplicates": True}) in client.calls
