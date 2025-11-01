from __future__ import annotations

import pytest

from video_playlist_downloader.throttle import ThrottleController, ThrottleProfile


def test_throttle_exponential_backoff_on_ban():
    sleeps: list[float] = []
    current = 0.0

    def fake_time() -> float:
        return current

    def fake_sleep(amount: float) -> None:
        nonlocal current
        sleeps.append(amount)
        current += amount

    profile = ThrottleProfile(
        max_concurrency=1,
        sleep_interval=0.0,
        ban_backoff_initial=1.0,
        ban_backoff_factor=2.0,
        ban_backoff_max=5.0,
    )
    controller = ThrottleController(profile, now=fake_time, sleeper=fake_sleep)

    with controller.guard() as ticket:
        ticket.mark_ban()

    with controller.guard() as ticket:
        ticket.mark_ban()

    with controller.guard() as ticket:
        ticket.mark_success()

    assert len(sleeps) == 2
    assert sleeps == pytest.approx([1.0, 2.0], rel=1e-2)
    metrics = controller.metrics
    assert metrics.ban_events == 2
    assert metrics.compliance_ratio < 1.0
