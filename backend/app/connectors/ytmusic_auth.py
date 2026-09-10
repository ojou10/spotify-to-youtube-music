from __future__ import annotations

import secrets
import time
from dataclasses import dataclass
from typing import Any

from app.connectors.base import AuthenticationRequired, ConnectorError, ValidationFailure
from app.settings.secrets import AtomicSecretStore


@dataclass(frozen=True)
class DeviceAuthChallenge:
    challenge_id: str
    user_code: str
    verification_url: str
    interval: int
    expires_at: int


@dataclass(frozen=True)
class YouTubeAuthPoll:
    status: str
    retry_after: int | None = None


class YouTubeMusicAuth:
    def __init__(self, store: AtomicSecretStore, credentials_factory=None):
        self.store = store
        self.credentials_factory = credentials_factory

    def _credentials(self, client_id: str, client_secret: str):
        if not client_id.strip() or not client_secret.strip():
            raise ValidationFailure("YouTube Music client ID and client secret are required")
        if self.credentials_factory:
            return self.credentials_factory(client_id, client_secret)
        from ytmusicapi import OAuthCredentials

        return OAuthCredentials(client_id, client_secret)

    def begin(self, client_id: str, client_secret: str) -> DeviceAuthChallenge:
        credentials = self._credentials(client_id, client_secret)
        try:
            code = credentials.get_code()
        except Exception as exc:
            raise ConnectorError("youtube_auth_start_failed", "YouTube Music authorization could not be started") from exc
        challenge_id = secrets.token_urlsafe(24)
        expires_in = int(code.get("expires_in", 600))
        pending = {
            "client_id": client_id,
            "client_secret": client_secret,
            "device_code": code["device_code"],
            "interval": int(code.get("interval", 5)),
            "expires_at": int(time.time()) + expires_in,
            "next_poll_at": 0,
        }
        self.store.write(f"youtube_challenge_{challenge_id}", pending)
        return DeviceAuthChallenge(challenge_id, code["user_code"], code.get("verification_url", code.get("verification_url_complete", "https://google.com/device")), int(pending["interval"]), pending["expires_at"])

    def poll(self, challenge_id: str) -> YouTubeAuthPoll:
        key = f"youtube_challenge_{challenge_id}"
        pending = self.store.read(key)
        if not pending:
            raise AuthenticationRequired("YouTube Music authorization challenge was not found")
        now = int(time.time())
        if now >= int(pending["expires_at"]):
            self.store.delete(key)
            return YouTubeAuthPoll("expired")
        if now < int(pending.get("next_poll_at", 0)):
            return YouTubeAuthPoll("pending", int(pending["next_poll_at"]) - now)
        credentials = self._credentials(pending["client_id"], pending["client_secret"])
        try:
            token = credentials.token_from_code(pending["device_code"])
        except Exception as exc:
            message = str(exc).lower()
            error = str(getattr(exc, "error", "")).lower()
            combined = f"{message} {error}"
            if "authorization_pending" in combined or "pending" in combined:
                pending["next_poll_at"] = now + int(pending["interval"])
                self.store.write(key, pending)
                return YouTubeAuthPoll("pending", int(pending["interval"]))
            if "slow_down" in combined or "slow down" in combined:
                pending["interval"] = int(pending["interval"]) + 5
                pending["next_poll_at"] = now + int(pending["interval"])
                self.store.write(key, pending)
                return YouTubeAuthPoll("slow_down", int(pending["interval"]))
            if "expired" in combined:
                self.store.delete(key)
                return YouTubeAuthPoll("expired")
            if "denied" in combined:
                self.store.delete(key)
                return YouTubeAuthPoll("denied")
            raise ConnectorError("youtube_auth_poll_failed", "YouTube Music authorization could not be completed") from exc
        if not token.get("access_token") or not token.get("refresh_token"):
            raise ConnectorError("youtube_auth_response_invalid", "YouTube Music returned an invalid authorization response")
        self.store.write("youtube_session", {**token, "client_id": pending["client_id"], "client_secret": pending["client_secret"]})
        self.store.delete(key)
        return YouTubeAuthPoll("success")

    def session(self) -> dict[str, Any] | None:
        value = self.store.read("youtube_session")
        return value if value and value.get("refresh_token") else None

    def disconnect(self) -> None:
        self.store.delete("youtube_session")
        for key in self.store.keys(prefix="youtube_challenge_"):
            self.store.delete(key)
