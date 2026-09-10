from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.persistence.db import Database
from app.persistence.repositories import RepositorySet
from app.settings.secrets import AtomicSecretStore


def test_history_detail_and_export_routes(tmp_path: Path):
    database = Database(tmp_path / "playlist.sqlite3")
    database.create_all()
    with database.session() as session:
        job = RepositorySet(session).jobs.add(status="completed", source_url="spotify:playlist:p", source_name="Playlist", source_track_count=0)
        job_id = job.id
    app = create_app(AtomicSecretStore(tmp_path / "secrets.json"), database)
    with TestClient(app) as client:
        assert client.get("/api/transfers").json()["items"][0]["id"] == job_id
        assert client.get(f"/api/transfers/{job_id}").json()["status"] == "completed"
        response = client.get(f"/api/transfers/{job_id}/exports/json")
    assert response.status_code == 200
    assert response.json()["schema_version"] == 1
