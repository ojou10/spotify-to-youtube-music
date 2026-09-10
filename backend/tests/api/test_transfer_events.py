from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.persistence.db import Database
from app.persistence.repositories import RepositorySet
from app.settings.secrets import AtomicSecretStore


def test_transfer_events_emit_safe_canonical_progress(tmp_path: Path):
    database = Database(tmp_path / "playlist.sqlite3")
    database.create_all()
    with database.session() as session:
        job = RepositorySet(session).jobs.add(status="matching", source_url="spotify:playlist:p", source_track_count=1, counts={"done": 0})
        job_id = job.id
    app = create_app(AtomicSecretStore(tmp_path / "secrets.json"), database)
    with TestClient(app) as client:
        response = client.get(f"/api/transfers/{job_id}/events")
    assert response.status_code == 200
    assert "event: progress" in response.text
    assert job_id in response.text
    assert "heartbeat" in response.text
