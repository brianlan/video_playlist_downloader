from __future__ import annotations

import pytest

from video_playlist_downloader import cli
from video_playlist_downloader.downloader import DownloadSummary


@pytest.mark.usefixtures("storage_root")
def test_download_cli_invokes_downloader(monkeypatch, cli_runner, app_config):
    playlist_url = "https://example.com/playlist"
    summary = DownloadSummary(
        total=5,
        completed=4,
        skipped=1,
        failed=0,
        pending=0,
        throttle_label="2 concurrent @2M",
        elapsed_seconds=12.0,
        eta_seconds=0.0,
    )

    monkeypatch.setattr(cli, "_load_configuration", lambda _: app_config)

    init_kwargs = {}
    run_kwargs = {}

    class StubDownloader:
        def __init__(self, *, config, playlist_url: str) -> None:
            init_kwargs["config"] = config
            init_kwargs["playlist_url"] = playlist_url

        def run(
            self,
            *,
            max_concurrency: int | None = None,
            limit_rate: str | None = None,
        ):
            run_kwargs["max_concurrency"] = max_concurrency
            run_kwargs["limit_rate"] = limit_rate
            return summary

    monkeypatch.setattr(cli, "PlaylistDownloader", StubDownloader)

    result = cli_runner.invoke(
        cli.app,
        [
            "download",
            playlist_url,
            "--max-concurrency",
            "3",
            "--limit-rate",
            "2M",
        ],
    )

    assert result.exit_code == 0
    assert init_kwargs.get("config") is app_config
    assert init_kwargs.get("playlist_url") == playlist_url
    assert run_kwargs.get("max_concurrency") == 3
    assert run_kwargs.get("limit_rate") == "2M"
    assert (app_config.storage.downloads).exists(), "Download directory should be created"
    assert "Download Summary" in result.stdout
    assert "Completed" in result.stdout
    assert "Skipped" in result.stdout
