from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

from app.connectors.base import ConnectorError, ValidationFailure
from app.connectors.spotify_auth import SpotifyAuth
from app.domain.enums import SupportStatus
from app.domain.models import PlaylistPreview, SourceItemValue, SpotifyUser


def parse_spotify_playlist_id(value: str) -> str:
    candidate = value.strip()
    if candidate.startswith("spotify:playlist:"):
        playlist_id = candidate.removeprefix("spotify:playlist:")
    else:
        parsed = urlparse(candidate)
        if parsed.scheme != "https" or parsed.netloc.lower() not in {"open.spotify.com", "play.spotify.com"}:
            raise ValidationFailure("Use a Spotify playlist URL or spotify:playlist URI")
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2 or parts[0] != "playlist":
            raise ValidationFailure("The URL must point to a Spotify playlist")
        playlist_id = parts[1]
    if not playlist_id or any(char not in "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_-" for char in playlist_id):
        raise ValidationFailure("The Spotify playlist ID is invalid")
    return playlist_id


@dataclass(frozen=True)
class SpotifyPlaylistPage:
    items: tuple[SourceItemValue, ...]
    total: int
    next_offset: int | None
    snapshot_id: str | None


class SpotifyConnector:
    def __init__(self, auth: SpotifyAuth, http_client: httpx.Client | None = None):
        self.auth = auth
        self.http_client = http_client or httpx.Client(timeout=20)

    def _get(self, path: str, **params) -> dict:
        response = self.http_client.get(
            f"https://api.spotify.com/v1{path}",
            params=params or None,
            headers={"Authorization": f"Bearer {self.auth.access_token()}"},
        )
        if response.status_code in {401, 403, 404, 429} or response.status_code >= 500:
            retryable = response.status_code == 429 or response.status_code >= 500
            code = {401: "spotify_auth_required", 403: "spotify_forbidden", 404: "spotify_not_found", 429: "spotify_rate_limited"}.get(response.status_code, "spotify_unavailable")
            raise ConnectorError(code, "Spotify could not complete this request", retryable=retryable)
        if response.status_code >= 400:
            raise ConnectorError("spotify_request_failed", "Spotify rejected this request")
        return response.json()

    def current_user(self) -> SpotifyUser:
        body = self._get("/me")
        return SpotifyUser(id=str(body["id"]), display_name=body.get("display_name"))

    def playlist_preview(self, playlist_id: str) -> PlaylistPreview:
        body = self._get(f"/playlists/{playlist_id}", fields="id,name,owner,public,tracks.total,snapshot_id,external_urls,images")
        owner = body.get("owner") or {}
        images = body.get("images") or []
        return PlaylistPreview(
            playlist_id=body["id"], name=body.get("name") or "Untitled playlist", owner_id=str(owner.get("id") or ""),
            owner_name=owner.get("display_name") or owner.get("id"), public=bool(body.get("public")),
            total=int((body.get("tracks") or {}).get("total", 0)),
            spotify_url=(body.get("external_urls") or {}).get("spotify") or f"https://open.spotify.com/playlist/{playlist_id}",
            artwork_url=(images[0] or {}).get("url") if images else None, snapshot_id=body.get("snapshot_id"),
        )

    def page(self, playlist_id: str, offset: int = 0, limit: int = 50) -> SpotifyPlaylistPage:
        body = self._get(f"/playlists/{playlist_id}/items", limit=min(limit, 50), offset=offset, fields="items(track,item),total,next")
        values = [self._map_item(raw, position) for position, raw in enumerate(body.get("items") or [], start=offset)]
        next_offset = offset + len(values) if body.get("next") else None
        return SpotifyPlaylistPage(tuple(values), int(body.get("total", 0)), next_offset, None)

    def iter_items(self, playlist_id: str, start_offset: int = 0) -> Iterator[SourceItemValue]:
        offset = start_offset
        while True:
            page = self.page(playlist_id, offset)
            yield from page.items
            if page.next_offset is None:
                break
            offset = page.next_offset

    @staticmethod
    def _map_item(raw: dict, position: int) -> SourceItemValue:
        track = raw.get("track") or raw.get("item")
        if not track:
            return SourceItemValue(position, None, "Unavailable item", (), None, None, None, SupportStatus.UNSUPPORTED, "unavailable")
        kind = track.get("type")
        title = track.get("name") or "Unavailable item"
        artists = tuple(artist.get("name", "") for artist in track.get("artists") or [] if artist.get("name"))
        album = (track.get("album") or {}).get("name")
        spotify_id = track.get("id")
        if track.get("is_local"):
            status, reason, spotify_id = SupportStatus.UNSUPPORTED, "local_file", None
        elif kind != "track":
            status, reason = SupportStatus.UNSUPPORTED, "episode"
        elif not spotify_id:
            status, reason = SupportStatus.UNSUPPORTED, "unavailable"
        else:
            status, reason = SupportStatus.SUPPORTED, None
        external = track.get("external_ids") or {}
        return SourceItemValue(position, spotify_id, title, artists, album, track.get("duration_ms"), external.get("isrc"), status, reason)
