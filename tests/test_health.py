"""Tests for the hardened /health endpoints.

The public /health MUST return only {status, service} (design decision D6 and
mcp-server-runtime spec). The authenticated /health/detail MUST include
version, build, git_commit, uptime_seconds, and tools.
"""

from __future__ import annotations

import os

import pytest
from starlette.testclient import TestClient


def _build_app(monkeypatch, api_key: str = "test-api-key"):
    """Fresh import of server.py with controlled env vars."""
    monkeypatch.setenv("TRANSPORT", "stdio")
    monkeypatch.setenv("MCP_API_KEY", api_key)
    monkeypatch.setenv("LORDICON_TOKEN", "test-token-12345")

    import importlib
    import mcp_lordicon.config as config_mod
    import mcp_lordicon.server as server_mod

    importlib.reload(config_mod)
    importlib.reload(server_mod)
    return server_mod


def test_public_health_returns_only_status_and_service(monkeypatch):
    server_mod = _build_app(monkeypatch)
    app = server_mod.mcp.http_app()
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload == {"status": "healthy", "service": "mcp-lordicon"}
    # Version fingerprinting keys must not appear
    for forbidden in ("version", "build", "git_commit", "uptime_seconds", "tools"):
        assert forbidden not in payload


def test_detail_health_requires_bearer_token(monkeypatch):
    server_mod = _build_app(monkeypatch, api_key="test-api-key")
    app = server_mod.mcp.http_app()
    client = TestClient(app)

    # No auth header → 401
    resp = client.get("/health/detail")
    assert resp.status_code == 401

    # Wrong token → 401
    resp = client.get(
        "/health/detail", headers={"Authorization": "Bearer wrong"}
    )
    assert resp.status_code == 401

    # Correct token → 200 with full payload
    resp = client.get(
        "/health/detail", headers={"Authorization": "Bearer test-api-key"}
    )
    assert resp.status_code == 200
    payload = resp.json()
    for required in ("version", "build", "git_commit", "uptime_seconds", "tools"):
        assert required in payload
    assert payload["status"] == "healthy"
    assert payload["service"] == "mcp-lordicon"
    assert payload["tools"] == 4
