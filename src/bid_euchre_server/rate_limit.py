"""A minimal in-memory, per-key fixed-window rate limiter.

Deliberately not a real dependency (slowapi/Redis/etc.) - this app runs as a
single process at friends-group scale (see CLAUDE.md's hosting notes), so an
in-memory dict is "cheap insurance against bots or accidental abuse," not a
scalability mechanism.
"""

from __future__ import annotations

import time


class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: float) -> None:
        self.max_calls = max_calls
        self.window_seconds = window_seconds
        self._calls: dict[str, list[float]] = {}

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        recent = [t for t in self._calls.get(key, []) if t > cutoff]
        if len(recent) >= self.max_calls:
            self._calls[key] = recent
            return False
        recent.append(now)
        self._calls[key] = recent
        return True
