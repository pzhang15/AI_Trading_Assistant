from __future__ import annotations

from typing import Any


class CoinbaseClient:
    """Placeholder Coinbase client. Does not perform any network calls yet."""

    def __init__(self, api_key: str | None = None, api_secret: str | None = None) -> None:
        self.api_key = api_key
        self.api_secret = api_secret

    def ping(self) -> dict[str, Any]:
        return {"service": "coinbase", "status": "stub"}


