"""Download-tracking tools: track_download + get_download_stats.

Deliberately does NOT import from mcp_lordicon.tools.search — the read/write
split (CDIT MCP Server Standards §7.6) is enforced at the module boundary so
that no search code path can cause a tracked event.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import Field

from mcp_lordicon.client import client
from mcp_lordicon.models.tracking import (
    DownloadStatsDay,
    DownloadStatsResult,
    DownloadTrackResult,
)

FamilyLiteral = Literal["system", "wired"]
StyleLiteral = Literal[
    "regular", "solid", "flat", "gradient", "lineal", "outline"
]


async def track_download(
    family: FamilyLiteral,
    style: StyleLiteral,
    index: Annotated[int, Field(ge=1)],
) -> DownloadTrackResult:
    """Report an icon download to Lordicon's billing API.

    Call this when an icon is actually embedded in a project — not when
    previewing search results. Free-icon downloads are unbilled on the Pro
    plan; premium-icon downloads count against your Lordicon subscription.

    This tool is never called automatically from search_icons: tracking is
    a user-driven action. A non-2xx response from Lordicon raises ValueError
    rather than returning a silent `tracked=false`.
    """
    await client.post_json(
        "/v1/download/track",
        family=family,
        style=style,
        index=index,
    )
    return DownloadTrackResult(
        tracked=True, family=family, style=style, index=index
    )


async def get_download_stats(
    limit: Annotated[int, Field(ge=1, le=100)] = 30,
    page: Annotated[int, Field(ge=1)] = 1,
) -> DownloadStatsResult:
    """Get daily free/premium download counts for billing visibility.

    Returns a paginated list of day entries, each with `date` (YYYY-MM-DD),
    `free`, and `premium` integer counts. Use this to monitor Lordicon Pro
    billing drift and verify `track_download` is being called at the
    expected rate.
    """
    body, headers = await client.get_with_meta(
        "/v1/download/stats",
        page=page,
        per_page=limit,
    )
    raw_list: list[dict[str, Any]] = body if isinstance(body, list) else []
    results = [
        DownloadStatsDay(
            date=item.get("date", "") or "",
            free=int(item.get("free", 0) or 0),
            premium=int(item.get("premium", 0) or 0),
        )
        for item in raw_list
    ]

    total = int(headers.get("X-Total-Count", headers.get("x-total-count", len(results))))
    current_page = int(headers.get("X-Page", headers.get("x-page", page)))
    per_page = int(headers.get("X-Per-Page", headers.get("x-per-page", limit)))
    next_page = current_page + 1 if current_page * per_page < total else None

    return DownloadStatsResult(
        results=results,
        total=total,
        page=current_page,
        next_page=next_page,
    )
