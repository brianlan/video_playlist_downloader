"""
Subtitle selection utilities.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence


def select_subtitle_tracks(
    tracks: Sequence[dict],
    preferred_languages: Iterable[str],
) -> List[dict]:
    """
    Filter available subtitle tracks based on preferred language ordering.

    Each preferred language is returned at most once. If no preferred languages are
    provided, all tracks are returned unchanged.
    """

    if not tracks:
        return []

    language_map = {}
    for track in tracks:
        language = track.get("language")
        if language and language not in language_map:
            language_map[language] = track

    selected: List[dict] = []
    for language in preferred_languages:
        if language in language_map:
            selected.append(language_map[language])

    if not selected:
        selected.extend(tracks)

    return selected


__all__ = ["select_subtitle_tracks"]
