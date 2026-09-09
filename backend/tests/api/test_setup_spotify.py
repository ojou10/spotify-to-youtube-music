from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.settings.secrets import AtomicSecretStore


def test_setup_status_redacts_tokens(tmp_path: Path):
    store = AtomicSecretStore(tmp_path / "secrets.json")
    store.write("spotify_session", {"client_id": "id", "access_token": "secret", "expires_at": 9999999999})
    with TestClient(create_app(store)) as client:
        body = client.get("/api/setup").json()
    assert "secret" not in str(body)
    assert body["spotify"]["connected"] is True


def test_start_returns_authorization_url_without_token(tmp_path: Path):
    store = AtomicSecretStore(tmp_path / "secrets.json")
    with TestClient(create_app(store)) as client:
        response = client.post("/api/setup/spotify/start", json={"client_id": "id"})
    assert response.status_code == 200
    assert response.json()["authorization_url"].startswith("https://accounts.spotify.com/authorize?")
