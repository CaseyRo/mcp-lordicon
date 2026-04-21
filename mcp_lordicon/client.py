"""Centralized async HTTP client for the Lordicon REST API.

Handles auth header injection, retries with exponential backoff on 429 and 5xx,
and surfaces pagination headers for endpoints that use header-based pagination.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from mcp_lordicon.config import settings

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BACKOFF_BASE = 2.0


class LordiconClient:
    """Async HTTP client for api.lordicon.com."""

    def __init__(self) -> None:
        token = settings.lordicon_token.get_secret_value()
        self._client = httpx.AsyncClient(
            base_url=settings.lordicon_url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            },
            timeout=30.0,
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Execute an HTTP request with retry + backoff. Returns the Response object.

        Callers that only need the parsed body should use `get_json` / `post_json`.
        Callers that need pagination headers should use `get_with_meta`.
        """
        last_exc: Exception | None = None
        for attempt in range(_MAX_RETRIES + 1):
            try:
                resp = await self._client.request(
                    method, path, params=params, json=json
                )
                if resp.status_code == 429:
                    wait = _BACKOFF_BASE ** (attempt + 1)
                    logger.warning("Rate limited (429), backing off %.1fs", wait)
                    last_exc = httpx.HTTPStatusError(
                        "429 Too Many Requests",
                        request=resp.request,
                        response=resp,
                    )
                    if attempt < _MAX_RETRIES:
                        await asyncio.sleep(wait)
                        continue
                    raise ValueError(
                        f"Upstream API error 429: rate limit exceeded after "
                        f"{_MAX_RETRIES} retries"
                    )
                if resp.status_code >= 500:
                    if attempt < _MAX_RETRIES:
                        wait = _BACKOFF_BASE ** (attempt + 1)
                        logger.warning(
                            "Server error %d, retry %d/%d in %.1fs",
                            resp.status_code,
                            attempt + 1,
                            _MAX_RETRIES,
                            wait,
                        )
                        await asyncio.sleep(wait)
                        last_exc = httpx.HTTPStatusError(
                            f"{resp.status_code}",
                            request=resp.request,
                            response=resp,
                        )
                        continue
                    raise ValueError(
                        f"Upstream API error {resp.status_code}: "
                        f"{resp.text[:200]}"
                    )
                if resp.status_code >= 400:
                    raise ValueError(
                        f"Upstream API error {resp.status_code}: "
                        f"{resp.text[:200]}"
                    )
                return resp
            except (httpx.ConnectError, httpx.ReadTimeout) as exc:
                if attempt < _MAX_RETRIES:
                    wait = _BACKOFF_BASE ** (attempt + 1)
                    logger.warning(
                        "Connection error, retry %d/%d in %.1fs",
                        attempt + 1,
                        _MAX_RETRIES,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    last_exc = exc
                    continue
                raise ValueError(f"Upstream API unreachable: {exc}") from exc
        if last_exc:
            raise ValueError(f"Upstream API error: {last_exc}") from last_exc
        raise RuntimeError("Retries exhausted without response")

    async def get_json(self, path: str, **params: Any) -> Any:
        """GET and return the parsed JSON body."""
        cleaned = {k: v for k, v in params.items() if v is not None}
        resp = await self._request("GET", path, params=cleaned or None)
        if resp.status_code == 204:
            return None
        return resp.json()

    async def get_with_meta(
        self, path: str, **params: Any
    ) -> tuple[Any, dict[str, str]]:
        """GET and return (parsed body, response headers).

        Used for endpoints that paginate via headers (`X-Total-Count`, `X-Page`, etc.).
        """
        cleaned = {k: v for k, v in params.items() if v is not None}
        resp = await self._request("GET", path, params=cleaned or None)
        body = None if resp.status_code == 204 else resp.json()
        return body, dict(resp.headers)

    async def post_json(self, path: str, **data: Any) -> Any:
        """POST JSON body; return the parsed response body (or None on 204)."""
        cleaned = {k: v for k, v in data.items() if v is not None}
        resp = await self._request("POST", path, json=cleaned or None)
        if resp.status_code == 204 or not resp.content:
            return None
        try:
            return resp.json()
        except ValueError:
            return None

    async def close(self) -> None:
        await self._client.aclose()


client = LordiconClient()
