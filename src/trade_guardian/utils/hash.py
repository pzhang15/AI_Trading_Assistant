from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel


def _to_serializable(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump(mode="json", by_alias=True, exclude_none=True)
    if isinstance(obj, (set, frozenset)):
        return sorted(list(obj))
    return obj


def compute_inputs_hash(data: Any) -> str:
    """
    Compute a stable SHA256 hash for the given input data.
    - For Pydantic models, uses model_dump with JSON mode, excluding Nones.
    - For general mappings/objects, falls back to json serialization with sorted keys.
    """
    canonical = json.dumps(
        _to_serializable(data),
        default=str,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


