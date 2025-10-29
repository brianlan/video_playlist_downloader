"""
Subtitle handling scaffolding.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SubtitleAsset:
    """Placeholder subtitle asset representation."""

    language_code: str
    format: str
    path: str
