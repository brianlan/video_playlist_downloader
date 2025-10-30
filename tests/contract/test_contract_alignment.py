from __future__ import annotations

import json
from uuid import NAMESPACE_URL, UUID, uuid5

import pytest

from video_playlist_downloader import cli
from video_playlist_downloader.downloader import DownloadSummary


@pytest.mark.usefixtures("storage_root")
def test_download_contract_payload(monkeypatch, cli_runner, app_config):
    playlist_url = "https://example.com/playlist"
    summary = DownloadSummary(
        total=2,
        completed=2,
        skipped=0,
        failed=0,
        pending=0,
        throttle_label="2 concurrent @ unbounded",
        elapsed_seconds=3.5,
        eta_seconds=0.0,
        applied_concurrency=app_config.throttle.max_concurrency,
        applied_limit_rate=app_config.throttle.limit_rate,
        sleep_interval=app_config.throttle.sleep_interval,
    )

    monkeypatch.setattr(cli, "_load_configuration", lambda _: app_config)

    class StubDownloader:
        def __init__(self, *, config, playlist_url: str) -> None:
            self.config = config
            self.playlist_url = playlist_url

        def run(self, *, max_concurrency=None, limit_rate=None):
            return summary

    monkeypatch.setattr(cli, "PlaylistDownloader", StubDownloader)

    result = cli_runner.invoke(
        cli.app,
        ["download", playlist_url, "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout.strip())

    assert set(payload.keys()) == {"sessionId", "playlistId", "enqueued"}
    UUID(payload["sessionId"])
    expected_playlist_id = str(uuid5(NAMESPACE_URL, playlist_url))
    assert payload["playlistId"] == expected_playlist_id
    assert payload["enqueued"] == summary.total


@pytest.mark.usefixtures("storage_root")
def test_status_contract_payload(monkeypatch, cli_runner, app_config):
    playlist_url = "https://example.com/playlist"
    summary = DownloadSummary(
        total=1,
        completed=1,
        skipped=0,
        failed=0,
        pending=0,
        throttle_label="2 concurrent @ unbounded",
        elapsed_seconds=1.0,
        eta_seconds=0.0,
        applied_concurrency=app_config.throttle.max_concurrency,
        applied_limit_rate=app_config.throttle.limit_rate,
        sleep_interval=app_config.throttle.sleep_interval,
    )

    monkeypatch.setattr(cli, "_load_configuration", lambda _: app_config)

    class StubDownloader:
        def __init__(self, *, config, playlist_url: str) -> None:
            self.config = config
            self.playlist_url = playlist_url

        def run(self, *, max_concurrency=None, limit_rate=None):
            return summary

    monkeypatch.setattr(cli, "PlaylistDownloader", StubDownloader)

    download_result = cli_runner.invoke(
        cli.app,
        ["download", playlist_url],
    )
    assert download_result.exit_code == 0

    status_result = cli_runner.invoke(
        cli.app,
        ["status", "--playlist-url", playlist_url, "--format", "json"],
    )
    assert status_result.exit_code == 0

    payload = json.loads(status_result.stdout.strip())
    expected_playlist_id = str(uuid5(NAMESPACE_URL, playlist_url))
    assert payload["playlistId"] == expected_playlist_id
    assert isinstance(payload["sessions"], list)
    assert payload["sessions"], "Expected at least one session in payload"

    session_payload = payload["sessions"][0]
    required_session_keys = {
        "sessionId",
        "status",
        "videosTotal",
        "videosCompleted",
        "videosSkipped",
        "videosFailed",
        "throttleProfile",
    }
    assert required_session_keys.issubset(session_payload.keys())
    assert session_payload["videosTotal"] == summary.total
    throttle_profile = session_payload["throttleProfile"]
    assert {
        "maxConcurrency",
        "limitRate",
        "sleepIntervalSeconds",
    }.issubset(throttle_profile.keys())
