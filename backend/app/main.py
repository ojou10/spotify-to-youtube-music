from pathlib import Path

from fastapi import FastAPI

from app.api.errors import connector_error_response
from app.api.health import router as health_router
from app.api.setup import router as setup_router
from app.api.spotify import router as spotify_router
from app.api.transfers import router as transfers_router
from app.connectors.base import ConnectorError
from app.connectors.spotify import SpotifyConnector
from app.connectors.spotify_auth import SpotifyAuth
from app.persistence.db import Database
from app.settings.paths import AppPaths
from app.settings.secrets import AtomicSecretStore
from app.spa import mount_frontend


def create_app(secret_store: AtomicSecretStore | None = None, database: Database | None = None) -> FastAPI:
    app = FastAPI(title="Playlist Bridge", version="0.1.0")
    paths = AppPaths.from_platform()
    store = secret_store or AtomicSecretStore(paths.secrets_file)
    app.state.spotify_auth = SpotifyAuth(store)
    app.state.database = database or Database(paths.root / "playlist_bridge.sqlite3")
    app.state.database.create_all()
    app.state.spotify_connector = SpotifyConnector(app.state.spotify_auth)
    app.include_router(health_router, prefix="/api")
    app.include_router(setup_router, prefix="/api")
    app.include_router(spotify_router, prefix="/api")
    app.include_router(transfers_router, prefix="/api")
    app.add_exception_handler(ConnectorError, connector_error_response)
    mount_frontend(app, Path(__file__).resolve().parents[2] / "frontend" / "dist")
    return app


app = create_app()
