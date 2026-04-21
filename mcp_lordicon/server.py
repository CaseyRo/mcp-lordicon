"""FastMCP server for Lordicon icon discovery.

Exposes four tools (search_icons, list_variants, track_download, get_download_stats)
and two health endpoints:

- GET /health — public, returns only {status, service}
- GET /health/detail — bearer-auth required; returns version/build/git_commit/uptime/tools

The public /health hardening matches the CDIT MCP Server Standards §13 recommendation
for Portal-exposed servers (see openspec design.md decision D6).
"""

from __future__ import annotations

import hmac
import os
from datetime import datetime, timezone

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from mcp_lordicon import __version__
from mcp_lordicon.auth import BearerTokenVerifier
from mcp_lordicon.config import settings
from mcp_lordicon.tools.search import list_variants, search_icons
from mcp_lordicon.tools.tracking import get_download_stats, track_download

_SERVICE_NAME = "mcp-lordicon"
_TOOL_COUNT = 4
_start_time = datetime.now(timezone.utc)


def _resolve_git_commit() -> str:
    """Resolution chain: GIT_COMMIT env → /app/.git_commit file → git rev-parse → unknown."""
    from_env = os.getenv("GIT_COMMIT", "")
    if from_env and from_env != "unknown":
        return from_env
    try:
        with open("/app/.git_commit") as f:
            val = f.read().strip()
            if val and val != "unknown":
                return val
    except FileNotFoundError:
        pass
    try:
        import subprocess

        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return "unknown"


_git_commit = _resolve_git_commit()
_build = (
    f"{__version__}+{_git_commit}"
    if _git_commit and _git_commit != "unknown"
    else __version__
)

_api_key = settings.mcp_api_key.get_secret_value()
if settings.transport == "http" and not _api_key:
    raise SystemExit(
        "MCP_API_KEY is required in HTTP mode. Refusing to start "
        "an unauthenticated server."
    )
_auth = BearerTokenVerifier(api_key=_api_key) if _api_key else None

mcp = FastMCP(_SERVICE_NAME, auth=_auth)

# Tools — register in read-then-write order
mcp.tool(search_icons)
mcp.tool(list_variants)
mcp.tool(track_download)
mcp.tool(get_download_stats)


@mcp.custom_route("/health", methods=["GET"])
async def health_public(request: Request) -> JSONResponse:
    """Public liveness probe. Version/build intentionally withheld (§13 hardening, D6)."""
    return JSONResponse({"status": "healthy", "service": _SERVICE_NAME})


@mcp.custom_route("/health/detail", methods=["GET"])
async def health_detail(request: Request) -> JSONResponse:
    """Authenticated detailed health payload. Requires matching Bearer token."""
    if _api_key:
        auth_header = request.headers.get("authorization", "")
        token = ""
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
        if not token or not hmac.compare_digest(token, _api_key):
            return JSONResponse(
                {"error": "unauthorized"}, status_code=401
            )
    uptime = int((datetime.now(timezone.utc) - _start_time).total_seconds())
    return JSONResponse(
        {
            "status": "healthy",
            "service": _SERVICE_NAME,
            "version": __version__,
            "build": _build,
            "git_commit": _git_commit,
            "uptime_seconds": uptime,
            "tools": _TOOL_COUNT,
        }
    )


def main() -> None:
    """Entry point. TRANSPORT=stdio for local dev, TRANSPORT=http for Docker/production."""
    if settings.transport == "http":
        mcp.run(
            transport="streamable-http",
            host=settings.host,
            port=settings.port,
            stateless_http=True,
        )
    else:
        mcp.run()


if __name__ == "__main__":
    main()
