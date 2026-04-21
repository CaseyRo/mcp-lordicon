"""Icon discovery tools: search_icons + list_variants."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Annotated, Any, Literal, Optional
from urllib.parse import urlparse

from pydantic import Field

from mcp_lordicon.client import client
from mcp_lordicon.models.icons import (
    IconEmbed,
    IconResult,
    IconSearchResult,
    VariantInfo,
)

FamilyLiteral = Literal["system", "wired"]
StyleLiteral = Literal[
    "regular", "solid", "flat", "gradient", "lineal", "outline"
]


def _extract_src_hash(json_url: str, family: str, style: str, index: int) -> str:
    """Best-effort stable-ish identifier for the icon.

    Lordicon's signed URLs embed a path segment that often correlates with
    the CDN hash pattern used by `cdn.lordicon.com/{hash}.json`. We extract
    the first non-trivial path segment as a best guess; if that fails, fall
    back to a human-readable `family-style-index` slug. The docstring on
    `search_icons` documents the caveat.
    """
    try:
        parsed = urlparse(json_url)
        parts = [p for p in PurePosixPath(parsed.path).parts if p and p != "/"]
        # Drop the filename (last) if present
        segments = [p for p in parts if not p.endswith(".json")]
        if segments:
            candidate = segments[-1]
            # Heuristic: hash-like segments are alphanumeric, 6–16 chars
            if candidate.isalnum() and 4 <= len(candidate) <= 32:
                return candidate
    except Exception:
        pass
    return f"{family}-{style}-{index}"


def _build_embed(
    json_url: str, family: str, style: str, index: int
) -> IconEmbed:
    src_hash = _extract_src_hash(json_url, family, style, index)
    web_component = (
        f'<lord-icon src="{json_url}" trigger="hover" '
        f'style="width:64px;height:64px"></lord-icon>'
    )
    react_player = (
        "import { Player } from '@lordicon/react';\n"
        f"// Fetch {json_url} and pass the parsed JSON as `icon`:\n"
        "<Player icon={ICON_DATA} trigger=\"hover\" />"
    )
    return IconEmbed(
        web_component=web_component,
        react_player=react_player,
        cdn_json_url=json_url,
        cdn_src_hash=src_hash,
    )


def _result_from_api(item: dict[str, Any]) -> IconResult:
    files = item.get("files") or {}
    json_url = files.get("json", "") or ""
    preview_url = files.get("preview", "") or ""
    family = item.get("family", "") or ""
    style = item.get("style", "") or ""
    index = int(item.get("index", 0) or 0)
    embed = _build_embed(json_url, family, style, index)
    return IconResult(
        family=family,
        style=style,
        index=index,
        name=item.get("name", "") or "",
        title=item.get("title", "") or "",
        premium=bool(item.get("premium", False)),
        preview_url=preview_url,
        embed=embed,
    )


async def search_icons(
    query: str,
    family: Optional[FamilyLiteral] = None,
    style: Optional[StyleLiteral] = None,
    premium: Optional[bool] = None,
    limit: Annotated[int, Field(ge=1, le=50)] = 10,
    page: Annotated[int, Field(ge=1)] = 1,
) -> IconSearchResult:
    """Search Lordicon icons by concept; returns paste-ready embed snippets inline.

    Use family='wired' for the large animated icon set, family='system' for UI
    glyphs. The most common combination is family='wired', style='outline'.
    Leave family and style unset to search across all variants.

    Each result includes a populated `embed` object with a `<lord-icon>` web-
    component snippet and a React Player snippet; copy either into code.
    The embed URLs are Lordicon-issued signed URLs with a limited lifespan —
    for long-lived pages, re-fetch or swap to a permanent CDN URL.

    Free icons are unbilled; premium icons count against your Lordicon Pro
    plan only when `track_download` is called.
    """
    params: dict[str, Any] = {
        "search": query,
        "page": page,
        "per_page": limit,
    }
    if family is not None:
        params["family"] = family
    if style is not None:
        params["style"] = style
    if premium is not None:
        params["premium"] = "true" if premium else "false"

    body, headers = await client.get_with_meta("/v1/icons", **params)
    raw_list = body if isinstance(body, list) else []
    results = [_result_from_api(item) for item in raw_list]

    total = int(headers.get("X-Total-Count", headers.get("x-total-count", len(results))))
    current_page = int(headers.get("X-Page", headers.get("x-page", page)))
    per_page = int(headers.get("X-Per-Page", headers.get("x-per-page", limit)))
    # Header-based pagination: another page exists if current * per_page < total
    next_page = current_page + 1 if current_page * per_page < total else None

    return IconSearchResult(
        results=results,
        total=total,
        page=current_page,
        next_page=next_page,
        query=query,
    )


async def list_variants() -> list[VariantInfo]:
    """List available Lordicon icon families and styles with free/premium counts.

    Use this before search to discover valid family/style combinations. The
    'wired' family carries the largest animated set with outline, flat,
    gradient, and lineal styles. The 'system' family carries UI system icons
    in regular and solid styles. Free counts are unbilled on the Pro plan.
    """
    body = await client.get_json("/v1/variants")
    if not isinstance(body, list):
        return []
    return [
        VariantInfo(
            family=item.get("family", "") or "",
            style=item.get("style", "") or "",
            free=int(item.get("free", 0) or 0),
            premium=int(item.get("premium", 0) or 0),
        )
        for item in body
    ]
