"""Tests for download-tracking tools (track_download, get_download_stats)."""

from __future__ import annotations

import importlib.util
from unittest.mock import AsyncMock, patch

import pytest

from mcp_lordicon.models.tracking import (
    DownloadStatsResult,
    DownloadTrackResult,
)
from mcp_lordicon.tools.tracking import get_download_stats, track_download


@pytest.mark.asyncio
async def test_track_download_returns_full_event_echo():
    with patch(
        "mcp_lordicon.tools.tracking.client.post_json",
        new=AsyncMock(return_value=None),
    ):
        result = await track_download(family="wired", style="outline", index=42)
    assert isinstance(result, DownloadTrackResult)
    assert result.tracked is True
    assert result.family == "wired"
    assert result.style == "outline"
    assert result.index == 42


@pytest.mark.asyncio
async def test_track_download_upstream_error_raises():
    with patch(
        "mcp_lordicon.tools.tracking.client.post_json",
        new=AsyncMock(side_effect=ValueError("Upstream API error 500: oops")),
    ):
        with pytest.raises(ValueError, match="Upstream API error"):
            await track_download(family="wired", style="outline", index=42)


@pytest.mark.asyncio
async def test_get_download_stats_returns_paginated_envelope(sample_stats_day):
    headers = {"X-Total-Count": "2", "X-Page": "1", "X-Per-Page": "30"}
    with patch(
        "mcp_lordicon.tools.tracking.client.get_with_meta",
        new=AsyncMock(return_value=([sample_stats_day, sample_stats_day], headers)),
    ):
        result = await get_download_stats(limit=30, page=1)
    assert isinstance(result, DownloadStatsResult)
    assert len(result.results) == 2
    assert result.total == 2
    assert result.page == 1
    assert result.next_page is None
    assert result.results[0].date == "2026-04-21"
    assert result.results[0].free == 12
    assert result.results[0].premium == 3


def _import_lines(origin_path: str) -> list[str]:
    """Return only lines that look like Python import statements."""
    lines: list[str] = []
    with open(origin_path) as f:
        for raw in f:
            stripped = raw.strip()
            if stripped.startswith(("import ", "from ")):
                lines.append(stripped)
    return lines


def test_tracking_module_does_not_import_search_module():
    """CDIT MCP Server Standards §7.6: reads/writes split at module boundary."""
    import mcp_lordicon.tools.tracking as tracking_mod

    origin = importlib.util.find_spec("mcp_lordicon.tools.tracking").origin
    imports = _import_lines(origin)

    assert not any("mcp_lordicon.tools.search" in line for line in imports), (
        f"tracking.py must not import from tools.search; saw: {imports}"
    )
    # Sanity check: the tracking module still imports client and models
    assert any("mcp_lordicon.client" in line for line in imports)
    assert any("mcp_lordicon.models.tracking" in line for line in imports)
    # Module loaded and exposes the expected tools
    assert hasattr(tracking_mod, "track_download")
    assert hasattr(tracking_mod, "get_download_stats")


def test_search_module_does_not_import_tracking_module():
    origin = importlib.util.find_spec("mcp_lordicon.tools.search").origin
    imports = _import_lines(origin)
    assert not any("mcp_lordicon.tools.tracking" in line for line in imports), (
        f"search.py must not import from tools.tracking; saw: {imports}"
    )
