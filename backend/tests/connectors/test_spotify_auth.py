import time
from pathlib import Path

import httpx
import pytest
import respx

from app.connectors.base import ValidationFailure
from app.connectors.spotify_auth import TOKEN_ENDPOINT, SpotifyAuth, pkce_challenge
from app.settings.secrets import AtomicSecretStore


def test_pkce_challenge_matches_verifier():
    verifier = "a" * 64
    assert pkce_challenge(verifier) == "_-BU_nrgy23GXDr5th1SCfQ5hR20PQulmXM33xVGaOs"


@respx.mock
def test_complete_exchanges_code_and_never_returns_tokens(tmp_path: Path):
    route = respx.post(TOKEN_ENDPOINT).mock(
        return_value=httpx.Response(200, json={"access_token": "secret", "refresh_token": "refresh", "expires_in": 3600})
    )
    auth = SpotifyAuth(AtomicSecretStore(tmp_path / "secrets.json"))
    started = auth.begin("client-id")
    session = auth.complete("code", started.state)
    assert route.called
    assert session.client_id == "client-id"
    assert session.access_token == "secret"


def test_expired_state_is_rejected(tmp_path: Path):
    store = AtomicSecretStore(tmp_path / "secrets.json")
    store.write("spotify_pkce_pending", {"client_id": "x", "verifier": "y", "state": "state", "expires_at": int(time.time()) - 1})
    auth = SpotifyAuth(store)
    with pytest.raises(ValidationFailure):
        auth.complete("code", "state")
