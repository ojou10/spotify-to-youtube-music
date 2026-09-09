from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.connectors.spotify_auth import SpotifyAuth

router = APIRouter(prefix="/setup")


class SpotifyClientId(BaseModel):
    client_id: str = Field(min_length=1, max_length=200)


def get_spotify_auth(request: Request) -> SpotifyAuth:
    return request.app.state.spotify_auth


@router.get("")
def setup_status(auth: Annotated[SpotifyAuth, Depends(get_spotify_auth)]):
    session = auth.session()
    return {
        "spotify": {
            "configured": bool(session),
            "connected": bool(session),
            "display_name": session.display_name if session else None,
        },
        "youtube": {"configured": False, "connected": False, "display_name": None},
    }


@router.post("/spotify/start")
def spotify_start(request: SpotifyClientId, auth: Annotated[SpotifyAuth, Depends(get_spotify_auth)]):
    result = auth.begin(request.client_id)
    return {"authorization_url": result.authorization_url, "state": result.state}


@router.get("/spotify/callback")
def spotify_callback(code: str, state: str, auth: Annotated[SpotifyAuth, Depends(get_spotify_auth)]):
    auth.complete(code, state)
    return RedirectResponse("http://127.0.0.1:5173/setup?spotify=connected", status_code=303)


@router.delete("/spotify")
def spotify_disconnect(auth: Annotated[SpotifyAuth, Depends(get_spotify_auth)]):
    auth.disconnect()
    return {"disconnected": True}
