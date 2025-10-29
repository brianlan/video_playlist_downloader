"""
Metadata management scaffolding for video records.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class VideoMetadata:
    """Placeholder structure for video metadata."""

    video_url: str
    title: str
    publish_time: Optional[datetime] = None
