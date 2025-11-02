from __future__ import annotations

from video_playlist_downloader import cli
from video_playlist_downloader.downloader import DownloadSummary
from video_playlist_downloader.throttle import ThrottleMetrics


def test_download_command_writes_throttle_report(monkeypatch, cli_runner, app_config, tmp_path):
    playlist_url = "https://example.com/playlist"
    metrics = ThrottleMetrics(
        total_requests=20,
        compliant_requests=19,
        ban_events=1,
        total_sleep_seconds=4.0,
        total_backoff_seconds=2.5,
    )
    summary = DownloadSummary(
        total=20,
        completed=19,
        skipped=1,
        failed=0,
        pending=0,
        throttle_label="2 concurrent @ 2M",
        elapsed_seconds=10.0,
        eta_seconds=0.0,
        applied_concurrency=2,
        applied_limit_rate="2M",
        sleep_interval=app_config.throttle.sleep_interval,
        throttle_metrics=metrics,
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
        [
            "download",
            playlist_url,
        ],
    )
    assert result.exit_code == 0

    report_path = app_config.storage.reports / "throttle-metrics.md"
    assert report_path.exists()
    contents = report_path.read_text(encoding="utf-8")
    assert "Compliance" in contents
    assert "95.00%" in contents
    assert "Ban events" in contents
