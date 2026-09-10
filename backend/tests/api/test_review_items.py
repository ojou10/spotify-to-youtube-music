from pathlib import Path

from fastapi.testclient import TestClient

from app.main import create_app
from app.persistence.db import Database
from app.persistence.repositories import RepositorySet
from app.settings.secrets import AtomicSecretStore


def test_review_items_endpoint_returns_cursor_and_strict_decision_validation(tmp_path: Path):
    database = Database(tmp_path / "playlist.sqlite3")
    database.create_all()
    with database.session() as session:
        job = RepositorySet(session).jobs.add(status="awaiting_review", revision=1, source_url="spotify:playlist:p", source_track_count=0)
        job_id = job.id
    app = create_app(AtomicSecretStore(tmp_path / "secrets.json"), database)
    with TestClient(app) as client:
        assert client.get(f"/api/transfers/{job_id}/items?limit=1").json() == {"items": [], "next_cursor": None}
        response = client.put(f"/api/transfers/{job_id}/items/nope/decision", json={"action": "not-valid"})
    assert response.status_code == 422
