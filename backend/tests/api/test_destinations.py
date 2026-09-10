from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.models import DestinationPlaylist
from app.main import create_app
from app.persistence.db import Database
from app.settings.secrets import AtomicSecretStore


class FakeYouTube:
    def list_owned_playlists(self):
        return [DestinationPlaylist("owned", "Owned", 2, True, "https://music.youtube.com/playlist?list=owned"), DestinationPlaylist("other", "Other", 1, False, None)]


def test_destinations_only_include_owned_playlists(tmp_path: Path):
    app = create_app(AtomicSecretStore(tmp_path / "secrets.json"), Database(tmp_path / "playlist.sqlite3"))
    app.state.youtube_connector = FakeYouTube()
    with TestClient(app) as client:
        response = client.get("/api/youtube/playlists")
    assert response.status_code == 200
    assert [item["playlist_id"] for item in response.json()["items"]] == ["owned"]
