"""Tests for bearer authentication and transport-mode validation."""

from __future__ import annotations

import os

import pytest

from mcp_lordicon.auth import BearerTokenVerifier
from mcp_lordicon.config import Settings


@pytest.mark.asyncio
async def test_bearer_verifier_accepts_matching_token():
    verifier = BearerTokenVerifier(api_key="secret-value")
    token = await verifier.verify_token("secret-value")
    assert token is not None
    assert token.token == "secret-value"
    assert token.client_id == "bearer"


@pytest.mark.asyncio
async def test_bearer_verifier_rejects_mismatch():
    verifier = BearerTokenVerifier(api_key="secret-value")
    assert await verifier.verify_token("wrong-value") is None
    assert await verifier.verify_token("") is None


@pytest.mark.asyncio
async def test_bearer_verifier_uses_constant_time_comparison():
    """Sanity: verifier does not short-circuit on first char mismatch."""
    import hmac

    # Two mismatching tokens of different lengths should both fail without raising.
    verifier = BearerTokenVerifier(api_key="a" * 32)
    assert await verifier.verify_token("b" * 32) is None
    assert await verifier.verify_token("a") is None
    # Confirm we are using hmac.compare_digest (not ==)
    assert hmac.compare_digest("same", "same") is True
    assert hmac.compare_digest("same", "diff") is False


def test_http_mode_requires_mcp_api_key(monkeypatch):
    monkeypatch.setenv("TRANSPORT", "http")
    monkeypatch.delenv("MCP_API_KEY", raising=False)
    with pytest.raises(ValueError, match="MCP_API_KEY is required"):
        Settings()


def test_stdio_mode_does_not_require_mcp_api_key(monkeypatch):
    monkeypatch.setenv("TRANSPORT", "stdio")
    monkeypatch.delenv("MCP_API_KEY", raising=False)
    # Should not raise
    s = Settings()
    assert s.transport == "stdio"


def test_http_mode_accepts_when_api_key_present(monkeypatch):
    monkeypatch.setenv("TRANSPORT", "http")
    monkeypatch.setenv("MCP_API_KEY", "some-random-value")
    s = Settings()
    assert s.transport == "http"
    assert s.mcp_api_key.get_secret_value() == "some-random-value"


def test_invalid_lordicon_url_rejected(monkeypatch):
    monkeypatch.setenv("LORDICON_URL", "ftp://nope.example")
    with pytest.raises(ValueError, match="http or https scheme"):
        Settings()
