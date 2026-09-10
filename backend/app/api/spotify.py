from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

from app.connectors.base import ValidationFailure
from app.connectors.spotify import SpotifyConnector, parse_spotify_playlist_id

router = APIRouter(prefix="/spotify", tags=["spotify"])


class InspectRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str


def _connector(request: Request) -> SpotifyConnector:
    return SpotifyConnector(request.app.state.spotify_auth)


@router.post("/inspect")
def inspect_playlist(payload: InspectRequest, request: Request):
    connector = _connector(request)
    playlist_id = parse_spotify_playlist_id(payload.url)
    preview = connector.playlist_preview(playlist_id)
    user = connector.current_user()
    if not preview.public:
        raise ValidationFailure("The Spotify playlist must be public")
    if preview.owner_id != user.id:
        raise ValidationFailure("Only playlists owned by the connected Spotify account can be imported")
    return {"playlist_id": preview.playlist_id, "name": preview.name, "owner_name": preview.owner_name, "public": preview.public, "total": preview.total, "spotify_url": preview.spotify_url, "artwork_url": preview.artwork_url, "snapshot_id": preview.snapshot_id}

