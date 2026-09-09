from pathlib import Path

from fastapi import FastAPI

from app.api.health import router as health_router
from app.spa import mount_frontend


def create_app() -> FastAPI:
    app = FastAPI(title="Playlist Bridge", version="0.1.0")
    app.include_router(health_router, prefix="/api")
    mount_frontend(app, Path(__file__).resolve().parents[2] / "frontend" / "dist")
    return app


app = create_app()
