from fastapi import APIRouter, Request

router = APIRouter(prefix="/youtube", tags=["youtube"])


@router.get("/playlists")
def youtube_playlists(request: Request):
    playlists = request.app.state.youtube_connector.list_owned_playlists()
    return {"items": [playlist.__dict__ for playlist in playlists if playlist.owned]}
