"""Pydantic models for icon search and variant responses."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class IconEmbed(BaseModel):
    """Ready-to-paste embed snippets for an icon.

    The `cdn_json_url` is the Lordicon-issued signed URL for the Lottie JSON.
    Signed URLs have a limited lifespan — for long-lived pages, re-fetch or
    swap to a permanent `cdn.lordicon.com/{hash}.json` URL once resolved.
    """

    web_component: str
    react_player: str
    cdn_json_url: str
    cdn_src_hash: str


class IconResult(BaseModel):
    """Single icon from the Lordicon catalog."""

    family: str
    style: str
    index: int
    name: str
    title: str
    premium: bool
    preview_url: str
    embed: IconEmbed


class IconSearchResult(BaseModel):
    """Paginated icon search results."""

    results: list[IconResult]
    total: int
    page: int
    next_page: Optional[int] = None
    query: str


class VariantInfo(BaseModel):
    """Icon family/style variant with free + premium counts."""

    family: str
    style: str
    free: int
    premium: int
