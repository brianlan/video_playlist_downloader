from __future__ import annotations

from video_playlist_downloader import metadata


def test_subtitle_coverage_report_calculates_percentage():
    coverage = metadata.generate_subtitle_coverage_report(
        total_videos=10,
        videos_with_subtitles=9,
        languages={"en": 7, "zh": 5},
    )

    assert coverage["coveragePercent"] == 90
    assert coverage["languages"]["en"] == 7
    assert coverage["languages"]["zh"] == 5


def test_subtitle_coverage_report_handles_zero_total():
    coverage = metadata.generate_subtitle_coverage_report(
        total_videos=0,
        videos_with_subtitles=0,
        languages={},
    )
    assert coverage["coveragePercent"] == 0
