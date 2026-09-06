"""Run-level time budget and per-model circuit breaker for LLM calls (architecture.md §28.2/§28.6)."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field


@dataclass
class RunDeadline:
    """Wall-clock budget shared by every LLM/embedding call of one run."""

    budget_s: float
    call_cap_s: float = 12.0
    min_retry_s: float = 8.0
    started: float = field(default_factory=time.monotonic)

    def remaining(self) -> float:
        return max(0.0, self.budget_s - (time.monotonic() - self.started))

    @property
    def expired(self) -> bool:
        return self.remaining() <= 0.0

    def call_timeout(self, cap: float | None = None) -> float:
        """Per-call timeout: min(cap, remaining − 2 s); ≤ 0 means "do not start another call"."""
        cap = self.call_cap_s if cap is None else cap
        return max(0.0, min(cap, self.remaining() - 2.0))

    def may_retry(self) -> bool:
        return self.remaining() >= self.min_retry_s


class CircuitBreaker:
    """Per-model breaker: `threshold` failures within `window_s` opens the model for `open_s`. In-process only."""

    def __init__(self, threshold: int = 3, window_s: float = 60.0, open_s: float = 120.0) -> None:
        self.threshold, self.window_s, self.open_s = threshold, window_s, open_s
        self._failures: dict[str, deque[float]] = {}
        self._open_until: dict[str, float] = {}

    def is_open(self, model: str) -> bool:
        until = self._open_until.get(model)
        if until is None:
            return False
        if time.monotonic() >= until:
            self._open_until.pop(model, None)
            self._failures.pop(model, None)
            return False
        return True

    def record_failure(self, model: str) -> None:
        now = time.monotonic()
        q = self._failures.setdefault(model, deque())
        q.append(now)
        while q and now - q[0] > self.window_s:
            q.popleft()
        if len(q) >= self.threshold:
            self._open_until[model] = now + self.open_s

    def record_success(self, model: str) -> None:
        self._failures.pop(model, None)
        self._open_until.pop(model, None)

    def reset(self) -> None:
        self._failures.clear()
        self._open_until.clear()

    def snapshot(self) -> dict[str, float]:
        """model → seconds until the breaker closes again (for /readyz)."""
        now = time.monotonic()
        return {m: round(u - now, 1) for m, u in self._open_until.items() if u > now}
