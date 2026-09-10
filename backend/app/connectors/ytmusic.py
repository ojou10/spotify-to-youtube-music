from __future__ import annotations

from app.connectors.base import AuthenticationRequired, ConnectorError
from app.connectors.ytmusic_auth import YouTubeMusicAuth
from app.domain.enums import Visibility
from app.domain.models import DestinationPlaylist, YTMCandidate


class YouTubeMusicConnector:
    def __init__(self, auth: YouTubeMusicAuth, client=None, client_factory=None):
        self.auth = auth
        self._client_instance = client
        self.client_factory = client_factory

    def _client(self):
        if self._client_instance is not None:
            return self._client_instance
        session = self.auth.session()
        if not session:
            raise AuthenticationRequired("Connect YouTube Music before continuing")
        if self.client_factory:
            self._client_instance = self.client_factory(session)
            return self._client_instance
        from ytmusicapi import OAuthCredentials, YTMusic

        credentials = OAuthCredentials(session["client_id"], session["client_secret"])
        self._client_instance = YTMusic(auth=session, oauth_credentials=credentials)
        return self._client_instance

    def search_songs(self, query: str, limit: int = 5) -> list[YTMCandidate]:
        try:
            rows = self._client().search(query, filter="songs", limit=limit)
        except Exception as exc:
            raise ConnectorError("youtube_search_failed", "YouTube Music search failed", retryable=True) from exc
        return [self._map_song(row) for row in rows if row.get("videoId")]

    def list_owned_playlists(self) -> list[DestinationPlaylist]:
        try:
            rows = self._client().get_library_playlists(limit=None)
        except Exception as exc:
            raise ConnectorError("youtube_playlists_failed", "YouTube Music playlists could not be loaded", retryable=True) from exc
        return [DestinationPlaylist(str(row["playlistId"]), row.get("title") or "Untitled playlist", int(row.get("count", 0)), True, f"https://music.youtube.com/playlist?list={row['playlistId']}") for row in rows if row.get("playlistId")]

    def get_playlist(self, playlist_id: str, limit: int | None = None) -> dict:
        try:
            return self._client().get_playlist(playlist_id, limit=limit)
        except Exception as exc:
            raise ConnectorError("youtube_playlist_failed", "YouTube Music playlist could not be loaded", retryable=True) from exc

    def create_playlist(self, title: str, description: str, visibility: Visibility) -> DestinationPlaylist:
        try:
            playlist_id = self._client().create_playlist(title, description, "PUBLIC" if visibility == Visibility.PUBLIC else "PRIVATE")
        except Exception as exc:
            raise ConnectorError("youtube_playlist_create_failed", "YouTube Music playlist could not be created", retryable=True) from exc
        return DestinationPlaylist(str(playlist_id), title, 0, True, f"https://music.youtube.com/playlist?list={playlist_id}")

    def append_video_ids(self, playlist_id: str, video_ids: list[str]) -> None:
        if not video_ids:
            return
        try:
            self._client().add_playlist_items(playlist_id, video_ids, duplicates=True)
        except Exception as exc:
            raise ConnectorError("youtube_playlist_append_failed", "YouTube Music playlist could not be updated", retryable=True) from exc

    def test_connection(self) -> bool:
        self._client().get_library_playlists(limit=1)
        return True

    @staticmethod
    def _map_song(row: dict) -> YTMCandidate:
        artists = row.get("artists") or []
        artist_names = tuple(item.get("name", "") if isinstance(item, dict) else str(item) for item in artists)
        album = row.get("album")
        if isinstance(album, dict):
            album = album.get("name")
        duration_ms = row.get("duration_ms")
        if duration_ms is None and row.get("duration_seconds") is not None:
            duration_ms = int(row["duration_seconds"]) * 1000
        return YTMCandidate(
            video_id=str(row["videoId"]), title=row.get("title") or "Untitled", artists=artist_names,
            album=album, duration_ms=duration_ms, result_type=row.get("resultType") or "song",
            thumbnail_url=(row.get("thumbnails") or [{}])[0].get("url"), url=f"https://music.youtube.com/watch?v={row['videoId']}",
        )
