"""Pydantic models for download-tracking responses."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class DownloadTrackResult(BaseModel):
    """Echo of a successful download-tracking call."""

    tracked: bool
    family: str
    style: str
    index: int


class DownloadStatsDay(BaseModel):
    """A single day's free/premium download counts."""

    date: str
    free: int
    premium: int


class DownloadStatsResult(BaseModel):
    """Paginated download statistics."""

    results: list[DownloadStatsDay]
    total: int
    page: int
    next_page: Optional[int] = None
