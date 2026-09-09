import base64
import hashlib
import secrets
import time
from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.connectors.base import AuthenticationRequired, ConnectorError, ValidationFailure
from app.settings.secrets import AtomicSecretStore

AUTH_ENDPOINT = "https://accounts.spotify.com/authorize"
TOKEN_ENDPOINT = "https://accounts.spotify.com/api/token"
API_SCOPE = "playlist-read-private user-read-private"


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def pkce_challenge(verifier: str) -> str:
    return _base64url(hashlib.sha256(verifier.encode("ascii")).digest())


@dataclass(frozen=True)
class SpotifyAuthStart:
    authorization_url: str
    state: str


@dataclass(frozen=True)
class SpotifySession:
    client_id: str
    access_token: str
    refresh_token: str | None
    expires_at: int
    display_name: str | None = None
    user_id: str | None = None


class SpotifyAuth:
    def __init__(
        self,
        store: AtomicSecretStore,
        redirect_uri: str = "http://127.0.0.1:8765/api/setup/spotify/callback",
        http_client: httpx.Client | None = None,
    ):
        self.store = store
        self.redirect_uri = redirect_uri
        self.http_client = http_client or httpx.Client(timeout=20)

    def begin(self, client_id: str) -> SpotifyAuthStart:
        if not client_id.strip():
            raise ValidationFailure("Spotify client ID is required")
        verifier = _base64url(secrets.token_bytes(48))
        state = _base64url(secrets.token_bytes(32))
        self.store.write(
            "spotify_pkce_pending",
            {"client_id": client_id, "verifier": verifier, "state": state, "expires_at": int(time.time()) + 600},
        )
        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "scope": API_SCOPE,
            "state": state,
            "code_challenge_method": "S256",
            "code_challenge": pkce_challenge(verifier),
        }
        return SpotifyAuthStart(f"{AUTH_ENDPOINT}?{urlencode(params)}", state)

    def complete(self, code: str, state: str) -> SpotifySession:
        pending = self.store.read("spotify_pkce_pending")
        if not pending or pending.get("state") != state or int(pending.get("expires_at", 0)) < int(time.time()):
            raise ValidationFailure("Spotify authorization state is invalid or expired")
        response = self.http_client.post(
            TOKEN_ENDPOINT,
            data={
                "client_id": pending["client_id"],
                "code": code,
                "redirect_uri": self.redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": pending["verifier"],
            },
        )
        if response.status_code != 200:
            raise ConnectorError("spotify_token_exchange_failed", "Spotify authorization could not be completed")
        body = response.json()
        access_token = body.get("access_token")
        if not access_token:
            raise ConnectorError("spotify_token_response_invalid", "Spotify returned no access token")
        session = {
            "client_id": pending["client_id"],
            "access_token": access_token,
            "refresh_token": body.get("refresh_token"),
            "expires_at": int(time.time()) + int(body.get("expires_in", 3600)),
        }
        self.store.write("spotify_session", session)
        self.store.delete("spotify_pkce_pending")
        return SpotifySession(**session)

    def session(self) -> SpotifySession | None:
        value = self.store.read("spotify_session")
        if not value or not value.get("access_token"):
            return None
        return SpotifySession(
            client_id=value["client_id"],
            access_token=value["access_token"],
            refresh_token=value.get("refresh_token"),
            expires_at=int(value.get("expires_at", 0)),
            display_name=value.get("display_name"),
            user_id=value.get("user_id"),
        )

    def access_token(self) -> str:
        session = self.session()
        if session is None:
            raise AuthenticationRequired("Connect Spotify before importing a playlist")
        if session.expires_at > int(time.time()) + 60:
            return session.access_token
        if not session.refresh_token:
            raise AuthenticationRequired("Reconnect Spotify to refresh your session")
        response = self.http_client.post(
            TOKEN_ENDPOINT,
            data={
                "client_id": session.client_id,
                "grant_type": "refresh_token",
                "refresh_token": session.refresh_token,
            },
        )
        if response.status_code != 200:
            raise AuthenticationRequired("Reconnect Spotify to refresh your session")
        body = response.json()
        refreshed = {
            **session.__dict__,
            "access_token": body["access_token"],
            "expires_at": int(time.time()) + int(body.get("expires_in", 3600)),
            "refresh_token": body.get("refresh_token", session.refresh_token),
        }
        self.store.write("spotify_session", refreshed)
        return refreshed["access_token"]

    def disconnect(self) -> None:
        self.store.delete("spotify_session")
        self.store.delete("spotify_pkce_pending")
