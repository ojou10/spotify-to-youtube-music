from pathlib import Path

import httpx
import respx
from fastapi.testclient import TestClient

from app.main import create_app
from app.persistence.db import Database
from app.settings.secrets import AtomicSecretStore


class Auth:
    def access_token(self):
        return "access"


def app_for(tmp_path: Path):
    app = create_app(AtomicSecretStore(tmp_path / "secrets.json"), Database(tmp_path / "playlist.sqlite3"))
    app.state.spotify_auth = Auth()
    return app


@respx.mock
def test_inspect_requires_owned_public_playlist(tmp_path: Path):
    respx.get("https://api.spotify.com/v1/playlists/p").mock(return_value=httpx.Response(200, json={"id": "p", "name": "Playlist", "public": True, "owner": {"id": "me", "display_name": "Me"}, "tracks": {"total": 2}, "snapshot_id": "snap", "external_urls": {"spotify": "https://open.spotify.com/playlist/p"}, "images": []}))
    respx.get("https://api.spotify.com/v1/me").mock(return_value=httpx.Response(200, json={"id": "me", "display_name": "Me"}))
    with TestClient(app_for(tmp_path)) as client:
        response = client.post("/api/spotify/inspect", json={"url": "https://open.spotify.com/playlist/p"})
    assert response.status_code == 200
    assert response.json()["total"] == 2


def test_inspect_rejects_extra_fields(tmp_path: Path):
    with TestClient(app_for(tmp_path)) as client:
        response = client.post("/api/spotify/inspect", json={"url": "spotify:playlist:p", "token": "secret"})
    assert response.status_code == 422
