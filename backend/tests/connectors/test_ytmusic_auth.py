from pathlib import Path

from app.connectors.ytmusic_auth import YouTubeMusicAuth
from app.settings.secrets import AtomicSecretStore


class Pending(Exception):
    pass


class SlowDown(Exception):
    pass


class FakeCredentials:
    next_error = None

    def __init__(self, client_id, client_secret):
        self.client_id = client_id
        self.client_secret = client_secret

    def get_code(self):
        return {"device_code": "device-secret", "user_code": "ABCD", "verification_url": "https://google.com/device", "interval": 1, "expires_in": 600}

    def token_from_code(self, device_code):
        if self.next_error:
            error, self.next_error = self.next_error, None
            raise error
        return {"access_token": "access-secret", "refresh_token": "refresh-secret", "expires_in": 3600, "token_type": "Bearer"}


def auth(tmp_path: Path):
    return YouTubeMusicAuth(AtomicSecretStore(tmp_path / "secrets.json"), FakeCredentials)


def test_successful_device_flow_never_returns_device_or_token(tmp_path: Path):
    youtube = auth(tmp_path)
    challenge = youtube.begin("client", "secret")
    assert challenge.user_code == "ABCD"
    assert not hasattr(challenge, "device_code")
    result = youtube.poll(challenge.challenge_id)
    assert result.status == "success"
    assert youtube.session()["refresh_token"] == "refresh-secret"


def test_pending_and_slow_down_states_are_safe(tmp_path: Path):
    youtube = auth(tmp_path)
    challenge = youtube.begin("client", "secret")
    FakeCredentials.next_error = Pending("authorization_pending")
    assert youtube.poll(challenge.challenge_id).status == "pending"
    pending = youtube.store.read(f"youtube_challenge_{challenge.challenge_id}")
    pending["next_poll_at"] = 0
    youtube.store.write(f"youtube_challenge_{challenge.challenge_id}", pending)
    FakeCredentials.next_error = SlowDown("slow_down")
    assert youtube.poll(challenge.challenge_id).status == "slow_down"


def test_expired_challenge_is_reported(tmp_path: Path):
    youtube = auth(tmp_path)
    challenge = youtube.begin("client", "secret")
    store = youtube.store
    pending = store.read(f"youtube_challenge_{challenge.challenge_id}")
    pending["expires_at"] = 0
    store.write(f"youtube_challenge_{challenge.challenge_id}", pending)
    assert youtube.poll(challenge.challenge_id).status == "expired"
