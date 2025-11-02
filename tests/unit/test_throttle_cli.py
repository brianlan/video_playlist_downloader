from __future__ import annotations

import json

import pytest

from video_playlist_downloader import cli
from video_playlist_downloader.downloader import DownloadSummary
from video_playlist_downloader.throttle import ThrottleMetrics


def test_download_command_surfaces_throttle_metrics(monkeypatch, cli_runner, app_config):
    playlist_url = "https://example.com/playlist"
    metrics = ThrottleMetrics(
        total_requests=10,
        compliant_requests=10,
        ban_events=0,
        total_sleep_seconds=1.2,
        total_backoff_seconds=0.0,
    )
    summary = DownloadSummary(
        total=10,
        completed=10,
        skipped=0,
        failed=0,
        pending=0,
        throttle_label="2 concurrent @ 2M",
        elapsed_seconds=6.0,
        eta_seconds=0.0,
        applied_concurrency=2,
        applied_limit_rate="2M",
        sleep_interval=app_config.throttle.sleep_interval,
        throttle_metrics=metrics,
    )

    def fake_config_loader(_path):
        return app_config

    class StubDownloader:
        def __init__(self, *, config, playlist_url: str) -> None:
            self.config = config
            self.playlist_url = playlist_url

        def run(self, *, max_concurrency=None, limit_rate=None):
            return summary

    monkeypatch.setattr(cli, "_load_configuration", fake_config_loader)
    monkeypatch.setattr(cli, "PlaylistDownloader", StubDownloader)

    result_text = cli_runner.invoke(
        cli.app,
        [
            "download",
            playlist_url,
            "--max-concurrency",
            "2",
            "--limit-rate",
            "2M",
        ],
    )

    assert result_text.exit_code == 0
    assert "Throttle compliance" in result_text.stdout
    assert "Ban events: 0" in result_text.stdout

    result_json = cli_runner.invoke(
        cli.app,
        [
            "download",
            playlist_url,
            "--max-concurrency",
            "2",
            "--limit-rate",
            "2M",
            "--format",
            "json",
        ],
    )

    assert result_json.exit_code == 0
    payload = json.loads(result_json.stdout)
    assert payload["throttle"]["complianceRatio"] == pytest.approx(metrics.compliance_ratio)
    assert payload["throttle"]["banEvents"] == 0
