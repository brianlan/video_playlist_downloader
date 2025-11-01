from __future__ import annotations

import threading
import time

import pytest

from video_playlist_downloader.throttle import ThrottleController, ThrottleProfile


def test_throttle_limits_parallel_slots():
    profile = ThrottleProfile(max_concurrency=1, sleep_interval=0.0)
    controller = ThrottleController(profile)

    entered_first = threading.Event()
    release_first = threading.Event()
    acquired_second = threading.Event()

    def first_worker() -> None:
        with controller.guard() as ticket:
            entered_first.set()
            release_first.wait(timeout=2)
            ticket.mark_success()

    def second_worker() -> None:
        entered_first.wait(timeout=2)
        with controller.guard() as ticket:
            acquired_second.set()
            ticket.mark_success()

    t1 = threading.Thread(target=first_worker)
    t2 = threading.Thread(target=second_worker)
    t1.start()
    t2.start()

    entered_first.wait(timeout=2)
    time.sleep(0.1)
    assert not acquired_second.is_set(), "Second worker should wait for semaphore release"

    release_first.set()
    t1.join(timeout=2)
    t2.join(timeout=2)

    assert acquired_second.is_set(), "Second worker should eventually acquire slot"
    metrics = controller.metrics
    assert metrics.total_requests == 2
    assert metrics.compliant_requests == 2


def test_throttle_respects_sleep_interval(monkeypatch):
    sleeps: list[float] = []
    current = 0.0

    def fake_time() -> float:
        return current

    def fake_sleep(amount: float) -> None:
        nonlocal current
        sleeps.append(amount)
        current += amount

    profile = ThrottleProfile(max_concurrency=1, sleep_interval=1.5)
    controller = ThrottleController(profile, now=fake_time, sleeper=fake_sleep)

    with controller.guard() as ticket:
        current += 0.25
        ticket.mark_success()

    with controller.guard() as ticket:
        ticket.mark_success()

    assert pytest.approx(sum(sleeps), rel=1e-3) == 1.5
    assert controller.metrics.total_requests == 2
