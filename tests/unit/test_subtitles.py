from __future__ import annotations

from video_playlist_downloader import subtitles


def test_extract_preferred_language_tracks():
    tracks = [
        {"language": "en", "url": "http://example.com/en.vtt"},
        {"language": "zh", "url": "http://example.com/zh.vtt"},
        {"language": "fr", "url": "http://example.com/fr.vtt"},
    ]

    result = subtitles.select_subtitle_tracks(
        tracks,
        preferred_languages=("zh", "en"),
    )

    assert [track["language"] for track in result] == ["zh", "en"]


def test_extract_subtitles_returns_empty_when_none_available():
    result = subtitles.select_subtitle_tracks([], preferred_languages=("en",))
    assert result == []
