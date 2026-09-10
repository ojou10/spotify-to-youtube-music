from __future__ import annotations

import random
import time
from collections.abc import Callable
from typing import TypeVar

from app.connectors.base import ConnectorError

T = TypeVar("T")


class RetryPolicy:
    def __init__(self, max_attempts: int = 5, base_delay: float = 1.0, max_delay: float = 60.0, *, sleep: Callable[[float], None] = time.sleep, jitter: Callable[[], float] | None = None):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.sleep = sleep
        self.jitter = jitter or (lambda: random.uniform(0, 0.25))

    def run(self, operation: Callable[[], T]) -> T:
        for attempt in range(self.max_attempts):
            try:
                return operation()
            except ConnectorError as exc:
                if not exc.retryable or attempt + 1 >= self.max_attempts:
                    raise
                retry_after = float(getattr(exc, "retry_after", 0) or 0)
                delay = min(self.max_delay, max(self.base_delay * (2**attempt), retry_after))
                self.sleep(delay + max(0.0, float(self.jitter())))
        raise AssertionError("retry loop did not return or raise")
