import json
from pathlib import Path

from app.settings.paths import AppPaths
from app.settings.secrets import AtomicSecretStore


def test_platform_path_is_not_the_repository(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("app.settings.paths.user_data_path", lambda *_: tmp_path / "app-data")
    assert AppPaths.from_platform().root == tmp_path / "app-data"


def test_store_writes_and_reads_one_key(tmp_path: Path):
    store = AtomicSecretStore(tmp_path / "secrets.json")
    store.write("spotify_session", {"access_token": "secret"})
    assert store.read("spotify_session") == {"access_token": "secret"}
    assert json.loads((tmp_path / "secrets.json").read_text())["spotify_session"]["access_token"] == "secret"
