from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.connectors.spotify_auth import SpotifyAuth
from app.connectors.ytmusic_auth import YouTubeMusicAuth

router = APIRouter(prefix="/setup")


class SpotifyClientId(BaseModel):
    client_id: str = Field(min_length=1, max_length=200)


class YouTubeClient(BaseModel):
    client_id: str = Field(min_length=1, max_length=300)
    client_secret: str = Field(min_length=1, max_length=300)


class YouTubePollRequest(BaseModel):
    challenge_id: str = Field(min_length=1, max_length=200)


def get_spotify_auth(request: Request) -> SpotifyAuth:
    return request.app.state.spotify_auth


def get_youtube_auth(request: Request) -> YouTubeMusicAuth:
    return request.app.state.youtube_auth


@router.get("")
def setup_status(auth: Annotated[SpotifyAuth, Depends(get_spotify_auth)], youtube: Annotated[YouTubeMusicAuth, Depends(get_youtube_auth)]):
    session = auth.session()
    youtube_session = youtube.session()
    return {
        "spotify": {"configured": bool(session), "connected": bool(session), "display_name": session.display_name if session else None},
        "youtube": {"configured": bool(youtube_session), "connected": bool(youtube_session), "display_name": None},
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


@router.post("/youtube/start")
def youtube_start(request: YouTubeClient, auth: Annotated[YouTubeMusicAuth, Depends(get_youtube_auth)]):
    challenge = auth.begin(request.client_id, request.client_secret)
    return {"challenge_id": challenge.challenge_id, "user_code": challenge.user_code, "verification_url": challenge.verification_url, "interval": challenge.interval, "expires_at": challenge.expires_at}


@router.post("/youtube/poll")
def youtube_poll(request: YouTubePollRequest, auth: Annotated[YouTubeMusicAuth, Depends(get_youtube_auth)]):
    result = auth.poll(request.challenge_id)
    return {"status": result.status, "retry_after": result.retry_after}


@router.post("/youtube/test")
def youtube_test(request: Request):
    return {"connected": request.app.state.youtube_connector.test_connection()}


@router.delete("/youtube")
def youtube_disconnect(auth: Annotated[YouTubeMusicAuth, Depends(get_youtube_auth)]):
    auth.disconnect()
    return {"disconnected": True}
