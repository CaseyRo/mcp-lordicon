"""Configuration loaded from environment variables."""

from __future__ import annotations

import logging
import warnings
from typing import Any, Literal
from urllib.parse import urlparse

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # Lordicon API connection
    lordicon_token: SecretStr = SecretStr("")
    lordicon_url: str = "https://api.lordicon.com"

    # Server transport
    transport: Literal["stdio", "http"] = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000

    # Bearer token auth for the MCP Portal (inbound)
    mcp_api_key: SecretStr = SecretStr("")

    model_config = {"env_prefix": "", "case_sensitive": False}

    @field_validator("lordicon_url")
    @classmethod
    def validate_lordicon_url(cls, v: str) -> str:
        parsed = urlparse(v)
        if parsed.scheme not in ("http", "https"):
            raise ValueError("LORDICON_URL must use http or https scheme")
        if not parsed.hostname:
            raise ValueError("LORDICON_URL must have a hostname")
        return v.rstrip("/")

    @model_validator(mode="after")
    def require_api_key_for_http(self) -> "Settings":
        if self.transport == "http" and not self.mcp_api_key.get_secret_value():
            raise ValueError(
                "MCP_API_KEY is required when TRANSPORT=http. "
                "Set the MCP_API_KEY environment variable."
            )
        return self

    def model_post_init(self, __context: Any) -> None:
        if not self.lordicon_token.get_secret_value():
            warnings.warn(
                "LORDICON_TOKEN is not set. API calls to Lordicon will fail.",
                stacklevel=2,
            )


settings = Settings()
