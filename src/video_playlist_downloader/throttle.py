"""
Throttle control scaffolding for download operations.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ThrottleProfile:
    """Placeholder data describing throttle parameters."""

    max_concurrency: int = 1
    limit_rate: str | None = None
    sleep_interval: float = 0.0


class ThrottleController:
    """Placeholder throttle controller doing no actual coordination."""

    def __init__(self, profile: ThrottleProfile | None = None) -> None:
        self.profile = profile or ThrottleProfile()

    def acquire(self) -> None:
        """Placeholder acquire operation."""
        return None

    def release(self) -> None:
        """Placeholder release operation."""
        return None
