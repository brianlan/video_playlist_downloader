from __future__ import annotations

from dataclasses import dataclass
import threading
import time
from typing import Callable, Optional


@dataclass(frozen=True)
class ThrottleProfile:
    """Configuration describing throttle behaviour."""

    max_concurrency: int = 1
    limit_rate: str | None = None
    sleep_interval: float = 0.0
    ban_backoff_initial: float = 0.0
    ban_backoff_factor: float = 2.0
    ban_backoff_max: float = 30.0


@dataclass
class ThrottleMetrics:
    """Aggregated telemetry emitted by the throttle controller."""

    total_requests: int = 0
    compliant_requests: int = 0
    throttled_requests: int = 0
    ban_events: int = 0
    total_sleep_seconds: float = 0.0
    total_backoff_seconds: float = 0.0

    @property
    def compliance_ratio(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return self.compliant_requests / self.total_requests

    def snapshot(self) -> ThrottleMetrics:
        return ThrottleMetrics(
            total_requests=self.total_requests,
            compliant_requests=self.compliant_requests,
            throttled_requests=self.throttled_requests,
            ban_events=self.ban_events,
            total_sleep_seconds=self.total_sleep_seconds,
            total_backoff_seconds=self.total_backoff_seconds,
        )

    def to_dict(self) -> dict[str, float | int]:
        return {
            "totalRequests": self.total_requests,
            "compliantRequests": self.compliant_requests,
            "throttledRequests": self.throttled_requests,
            "banEvents": self.ban_events,
            "totalSleepSeconds": self.total_sleep_seconds,
            "totalBackoffSeconds": self.total_backoff_seconds,
            "complianceRatio": self.compliance_ratio,
        }


class _ThrottleTicket:
    """Context manager managing a single throttled section."""

    def __init__(self, controller: ThrottleController) -> None:
        self._controller = controller
        self._outcome_recorded = False

    def __enter__(self) -> _ThrottleTicket:
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is not None:
            self.mark_failure()
        elif not self._outcome_recorded:
            self.mark_success()
        self._controller._release()
        return False

    def mark_success(self) -> None:
        if self._outcome_recorded:
            return
        self._controller._record_success()
        self._outcome_recorded = True

    def mark_failure(self) -> None:
        if self._outcome_recorded:
            return
        self._controller._record_failure()
        self._outcome_recorded = True

    def mark_ban(self) -> None:
        if self._outcome_recorded:
            return
        self._controller._record_ban()
        self._outcome_recorded = True


class ThrottleController:
    """
    Coordinate concurrent download slots while enforcing sleep intervals and ban recovery.
    """

    def __init__(
        self,
        profile: ThrottleProfile | None = None,
        *,
        now: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        self.profile = profile or ThrottleProfile()
        max_concurrency = max(1, self.profile.max_concurrency)
        self._now = now or time.perf_counter
        self._sleep = sleeper or time.sleep
        self._semaphore = threading.BoundedSemaphore(max_concurrency)
        self._lock = threading.Lock()
        self._active = 0
        self._last_release: Optional[float] = None
        self._current_backoff: float = 0.0
        self._metrics = ThrottleMetrics()

    def guard(self) -> _ThrottleTicket:
        """
        Acquire a throttle slot and return a context manager that records the outcome.
        """

        wait_time = self._prepare_wait()
        acquired = self._semaphore.acquire(timeout=None)
        if not acquired:  # pragma: no cover - BoundedSemaphore.acquire always returns True
            raise TimeoutError("Failed to acquire throttle semaphore.")
        with self._lock:
            self._metrics.total_requests += 1
            self._active += 1
        if wait_time > 0:
            with self._lock:
                self._metrics.throttled_requests += 1
        return _ThrottleTicket(self)

    def _prepare_wait(self) -> float:
        wait_time = 0.0
        now_value = self._now()
        with self._lock:
            if self._current_backoff > 0.0:
                wait_time += self._current_backoff
                self._metrics.total_backoff_seconds += self._current_backoff
            if self._last_release is not None and self.profile.sleep_interval > 0.0:
                elapsed = max(0.0, now_value - self._last_release)
                remaining = self.profile.sleep_interval - elapsed
                if remaining > 0.0:
                    wait_time += remaining
                    self._metrics.total_sleep_seconds += remaining

        if wait_time > 0.0:
            self._sleep(wait_time)
            # only keep backoff for consecutive bans; once we have slept the configured value,
            # we retain it until a success resets it.
        return wait_time

    def _release(self) -> None:
        with self._lock:
            self._active = max(0, self._active - 1)
            self._last_release = self._now()
        self._semaphore.release()

    def _record_success(self) -> None:
        with self._lock:
            self._metrics.compliant_requests += 1
            self._current_backoff = 0.0

    def _record_failure(self) -> None:
        # Failures count against compliance but do not trigger backoff.
        pass

    def _record_ban(self) -> None:
        with self._lock:
            self._metrics.ban_events += 1
            initial = self.profile.ban_backoff_initial
            factor = max(1.0, self.profile.ban_backoff_factor)
            maximum = max(initial, self.profile.ban_backoff_max)
            next_backoff = initial if self._current_backoff == 0.0 else self._current_backoff * factor
            self._current_backoff = min(maximum, next_backoff)

    @property
    def active(self) -> int:
        with self._lock:
            return self._active

    @property
    def metrics(self) -> ThrottleMetrics:
        with self._lock:
            return self._metrics.snapshot()


__all__ = ["ThrottleController", "ThrottleMetrics", "ThrottleProfile"]
