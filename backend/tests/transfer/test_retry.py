import pytest

from app.connectors.base import AuthenticationRequired, ConnectorError
from app.transfer.retry import RetryPolicy


def test_retry_policy_caps_attempts_and_uses_exponential_delays():
    attempts = 0
    delays = []

    def operation():
        nonlocal attempts
        attempts += 1
        raise ConnectorError("rate_limited", "try again", retryable=True)

    with pytest.raises(ConnectorError):
        RetryPolicy(max_attempts=5, base_delay=1, jitter=lambda: 0, sleep=delays.append).run(operation)
    assert attempts == 5
    assert delays == [1, 2, 4, 8]


def test_authentication_errors_are_not_retried():
    calls = []

    def operation():
        calls.append(1)
        raise AuthenticationRequired()

    with pytest.raises(AuthenticationRequired):
        RetryPolicy(sleep=lambda _: calls.append(99)).run(operation)
    assert calls == [1]


def test_retry_after_wins_but_is_capped():
    delays = []
    error = ConnectorError("rate_limited", "try again", retryable=True, retry_after=10)
    with pytest.raises(ConnectorError):
        RetryPolicy(max_attempts=2, base_delay=1, max_delay=5, jitter=lambda: 0, sleep=delays.append).run(lambda: (_ for _ in ()).throw(error))
    assert delays == [5]
