"""Helpers for stale-command and stale-telemetry leases."""

from __future__ import annotations

import time
from typing import Callable


class CommandLease:
    """Track whether a command or telemetry stream has gone stale."""

    def __init__(self, monotonic: Callable[[], float] | None = None) -> None:
        self._monotonic = monotonic or time.monotonic
        self._deadline = 0.0

    def renew(self, ttl_seconds: float) -> None:
        self._deadline = self._monotonic() + max(0.0, float(ttl_seconds))

    def clear(self) -> None:
        self._deadline = 0.0

    def expired(self) -> bool:
        if self._deadline == 0.0:
            return True
        return self._monotonic() >= self._deadline

    def remaining(self) -> float:
        if self._deadline == 0.0:
            return 0.0
        return max(0.0, self._deadline - self._monotonic())
