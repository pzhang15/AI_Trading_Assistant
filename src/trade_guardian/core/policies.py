from __future__ import annotations

from typing import Protocol

from trade_guardian.core.models import Asset


class Policy(Protocol):
    def evaluate(self, asset: Asset) -> bool:  # noqa: D401
        """Return True if the policy passes for the given asset."""
        ...


