"""Tests for LordiconClient: retry + backoff + error translation (Standards §5, §7.7)."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from mcp_lordicon.client import LordiconClient


def _mock_response(status_code: int, json_body=None, text: str = ""):
    """Build a Mock httpx.Response with the given status + body."""
    resp = AsyncMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.content = b"" if json_body is None and not text else b"body"
    resp.text = text
    resp.headers = {}
    resp.request = AsyncMock()
    if json_body is not None:
        resp.json = lambda: json_body
    return resp


@pytest.mark.asyncio
async def test_client_translates_4xx_to_value_error():
    """A client-side 4xx must raise ValueError with status + truncated body."""
    client = LordiconClient()
    resp = _mock_response(
        status_code=400,
        text="invalid query parameter 'family'",
    )
    with patch.object(client._client, "request", new=AsyncMock(return_value=resp)):
        with pytest.raises(ValueError, match="Upstream API error 400"):
            await client.get_json("/v1/icons", term="x")
    await client.close()


@pytest.mark.asyncio
async def test_client_retries_on_5xx_then_raises():
    """5xx responses retry up to _MAX_RETRIES, then surface a ValueError."""
    client = LordiconClient()
    err_resp = _mock_response(status_code=502, text="bad gateway")
    with patch.object(
        client._client,
        "request",
        new=AsyncMock(return_value=err_resp),
    ) as mock_req:
        with patch("mcp_lordicon.client.asyncio.sleep", new=AsyncMock()):
            with pytest.raises(ValueError, match="Upstream API error 502"):
                await client.get_json("/v1/icons")
    # _MAX_RETRIES=3 → 4 total calls (attempt 0, 1, 2, 3)
    assert mock_req.await_count == 4
    await client.close()


@pytest.mark.asyncio
async def test_client_retries_on_429_then_raises_rate_limit_error():
    """Repeated 429 must eventually raise a rate-limit-specific ValueError."""
    client = LordiconClient()
    err_resp = _mock_response(status_code=429, text="rate limited")
    with patch.object(
        client._client,
        "request",
        new=AsyncMock(return_value=err_resp),
    ) as mock_req:
        with patch("mcp_lordicon.client.asyncio.sleep", new=AsyncMock()):
            with pytest.raises(ValueError, match="429"):
                await client.get_json("/v1/icons")
    assert mock_req.await_count == 4
    await client.close()


@pytest.mark.asyncio
async def test_client_succeeds_after_transient_5xx():
    """One 5xx followed by 200 should succeed without raising."""
    client = LordiconClient()
    err_resp = _mock_response(status_code=500, text="oops")
    ok_resp = _mock_response(status_code=200, json_body={"ok": True})
    with patch.object(
        client._client,
        "request",
        new=AsyncMock(side_effect=[err_resp, ok_resp]),
    ):
        with patch("mcp_lordicon.client.asyncio.sleep", new=AsyncMock()):
            result = await client.get_json("/v1/icons")
    assert result == {"ok": True}
    await client.close()


@pytest.mark.asyncio
async def test_client_get_with_meta_returns_headers():
    """get_with_meta surfaces response headers for header-based pagination."""
    client = LordiconClient()
    resp = AsyncMock(spec=httpx.Response)
    resp.status_code = 200
    resp.content = b'[{"family":"wired"}]'
    resp.text = ""
    resp.headers = {"X-Total-Count": "200", "X-Page": "2", "X-Per-Page": "50"}
    resp.request = AsyncMock()
    resp.json = lambda: [{"family": "wired"}]
    with patch.object(client._client, "request", new=AsyncMock(return_value=resp)):
        body, headers = await client.get_with_meta("/v1/icons", page=2, per_page=50)
    assert body == [{"family": "wired"}]
    assert headers["X-Total-Count"] == "200"
    assert headers["X-Page"] == "2"
    await client.close()


@pytest.mark.asyncio
async def test_client_post_json_handles_201_without_body():
    """Lordicon's POST /v1/download/track returns 201 Created with no body."""
    client = LordiconClient()
    resp = AsyncMock(spec=httpx.Response)
    resp.status_code = 201
    resp.content = b""
    resp.text = ""
    resp.headers = {}
    resp.request = AsyncMock()
    with patch.object(client._client, "request", new=AsyncMock(return_value=resp)):
        result = await client.post_json(
            "/v1/download/track", family="wired", style="outline", index=1
        )
    assert result is None
    await client.close()


@pytest.mark.asyncio
async def test_client_retries_on_connection_error():
    """Transient connection errors should retry before surfacing as ValueError."""
    client = LordiconClient()
    err = httpx.ConnectError("connection reset")
    with patch.object(
        client._client, "request", new=AsyncMock(side_effect=err)
    ) as mock_req:
        with patch("mcp_lordicon.client.asyncio.sleep", new=AsyncMock()):
            with pytest.raises(ValueError, match="unreachable"):
                await client.get_json("/v1/icons")
    assert mock_req.await_count == 4
    await client.close()
