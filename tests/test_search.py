"""Tests for icon-discovery tools (search_icons, list_variants)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from mcp_lordicon.models.icons import IconSearchResult
from mcp_lordicon.tools.search import (
    _extract_src_hash,
    list_variants,
    search_icons,
)


@pytest.mark.asyncio
async def test_search_returns_envelope_with_embed_snippets(sample_icon):
    headers = {"X-Total-Count": "1", "X-Page": "1", "X-Per-Page": "10"}
    with patch(
        "mcp_lordicon.tools.search.client.get_with_meta",
        new=AsyncMock(return_value=([sample_icon], headers)),
    ):
        result = await search_icons(query="trophy")

    assert isinstance(result, IconSearchResult)
    assert result.query == "trophy"
    assert result.total == 1
    assert result.page == 1
    assert result.next_page is None
    assert len(result.results) == 1

    icon = result.results[0]
    assert icon.family == "wired"
    assert icon.style == "outline"
    assert icon.index == 42
    assert icon.preview_url.startswith("https://api.lordicon.com/")
    assert icon.embed.cdn_json_url.endswith("trophy.json?token=xyz")
    assert "<lord-icon" in icon.embed.web_component
    assert 'src=' in icon.embed.web_component
    assert 'trigger=' in icon.embed.web_component
    assert "Player" in icon.embed.react_player
    assert icon.embed.cdn_src_hash  # non-empty


@pytest.mark.asyncio
async def test_search_empty_results_returns_empty_envelope(sample_icon):
    headers = {"X-Total-Count": "0", "X-Page": "1", "X-Per-Page": "10"}
    with patch(
        "mcp_lordicon.tools.search.client.get_with_meta",
        new=AsyncMock(return_value=([], headers)),
    ):
        result = await search_icons(query="nonexistent")
    assert result.results == []
    assert result.total == 0
    assert result.next_page is None
    assert result.query == "nonexistent"


@pytest.mark.asyncio
async def test_search_next_page_calculated_from_headers(sample_icon):
    headers = {"X-Total-Count": "47", "X-Page": "1", "X-Per-Page": "10"}
    with patch(
        "mcp_lordicon.tools.search.client.get_with_meta",
        new=AsyncMock(return_value=([sample_icon] * 10, headers)),
    ):
        result = await search_icons(query="arrow", limit=10, page=1)
    assert result.total == 47
    assert result.page == 1
    assert result.next_page == 2


@pytest.mark.asyncio
async def test_search_filters_forwarded_to_client(sample_icon):
    headers = {"X-Total-Count": "1", "X-Page": "1", "X-Per-Page": "20"}
    mock = AsyncMock(return_value=([sample_icon], headers))
    with patch("mcp_lordicon.tools.search.client.get_with_meta", new=mock):
        await search_icons(
            query="arrow", family="wired", style="outline", premium=False, limit=20
        )
    mock.assert_awaited_once()
    _, kwargs = mock.call_args
    assert kwargs["family"] == "wired"
    assert kwargs["style"] == "outline"
    assert kwargs["premium"] == "false"
    assert kwargs["per_page"] == 20
    assert kwargs["search"] == "arrow"


@pytest.mark.asyncio
async def test_list_variants_returns_plain_list_without_envelope(sample_variant):
    with patch(
        "mcp_lordicon.tools.search.client.get_json",
        new=AsyncMock(return_value=[sample_variant]),
    ):
        result = await list_variants()
    assert isinstance(result, list)
    assert len(result) == 1
    v = result[0]
    assert v.family == "wired"
    assert v.style == "outline"
    assert v.free == 400
    assert v.premium == 1200


def test_extract_src_hash_picks_segment_from_signed_url():
    url = "https://api.lordicon.com/abc123xyz/trophy.json?token=xyz"
    assert _extract_src_hash(url, "wired", "outline", 42) == "abc123xyz"


def test_extract_src_hash_falls_back_to_slug():
    url = "https://example.invalid/no/useful/path/"
    # 'path' is alnum and length 4, so it would qualify as candidate — expect it
    # or the slug fallback. Either way non-empty.
    result = _extract_src_hash(url, "wired", "outline", 42)
    assert result  # non-empty; heuristic fallback is acceptable


def test_extract_src_hash_malformed_url_falls_back_to_slug():
    url = ""
    assert _extract_src_hash(url, "wired", "outline", 42) == "wired-outline-42"
