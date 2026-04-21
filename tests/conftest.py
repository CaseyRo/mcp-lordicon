"""Shared test fixtures."""

from __future__ import annotations

import os
from typing import Any

import pytest

# Set test env vars before any imports touch Settings.
os.environ.setdefault("LORDICON_TOKEN", "test-token-12345")
os.environ.setdefault("LORDICON_URL", "https://api.lordicon.com")


SAMPLE_ICON: dict[str, Any] = {
    "family": "wired",
    "style": "outline",
    "index": 42,
    "name": "trophy",
    "title": "Trophy",
    "premium": False,
    "files": {
        "preview": "https://api.lordicon.com/abc123/preview.png?token=xyz",
        "svg": "https://api.lordicon.com/abc123/trophy.svg?token=xyz",
        "json": "https://api.lordicon.com/abc123/trophy.json?token=xyz",
    },
}

SAMPLE_VARIANT: dict[str, Any] = {
    "family": "wired",
    "style": "outline",
    "free": 400,
    "premium": 1200,
}

SAMPLE_STATS_DAY: dict[str, Any] = {
    "date": "2026-04-21",
    "free": 12,
    "premium": 3,
}


@pytest.fixture
def sample_icon() -> dict[str, Any]:
    return dict(SAMPLE_ICON)


@pytest.fixture
def sample_variant() -> dict[str, Any]:
    return dict(SAMPLE_VARIANT)


@pytest.fixture
def sample_stats_day() -> dict[str, Any]:
    return dict(SAMPLE_STATS_DAY)
