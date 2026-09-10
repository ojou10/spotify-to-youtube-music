from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.persistence.db import Database
from app.settings.secrets import AtomicSecretStore


class FakeYoutubeAuth:
    def session(self):
        return None

    def begin(self, client_id, client_secret):
        return type("Challenge", (), {"challenge_id": "opaque", "user_code": "ABCD", "verification_url": "https://google.com/device", "interval": 5, "expires_at": 999})()

    def poll(self, challenge_id):
        return type("Poll", (), {"status": "pending", "retry_after": 5})()

    def disconnect(self):
        return None


class FakeYoutubeConnector:
    def test_connection(self):
        return True


def test_youtube_setup_does_not_expose_client_secret(tmp_path: Path):
    app = create_app(AtomicSecretStore(tmp_path / "secrets.json"), Database(tmp_path / "playlist.sqlite3"))
    app.state.youtube_auth = FakeYoutubeAuth()
    app.state.youtube_connector = FakeYoutubeConnector()
    with TestClient(app) as client:
        response = client.post("/api/setup/youtube/start", json={"client_id": "id", "client_secret": "secret"})
        assert response.status_code == 200
        body = response.json()
        assert body["challenge_id"] == "opaque"
        assert "client_secret" not in body
        assert client.post("/api/setup/youtube/poll", json={"challenge_id": "opaque"}).json()["status"] == "pending"
        assert client.post("/api/setup/youtube/test").json() == {"connected": True}
