from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


def mount_frontend(app: FastAPI, dist_dir: Path) -> None:
    """Serve a built React app without intercepting API routes."""
    if not dist_dir.is_dir():
        return

    assets = dist_dir / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="frontend-assets")

    @app.get("/{path:path}", include_in_schema=False)
    def frontend_navigation(path: str):
        if path.startswith("api/"):
            return None
        return FileResponse(dist_dir / "index.html")
