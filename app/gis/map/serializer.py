"""Canonical Deterministic JSON Serializer for Map-Ready Payloads."""

import json
from typing import Any, Dict, Optional, Union
from pydantic import BaseModel


def _sanitize_floats(obj: Any) -> Any:
    """Recursively replaces NaN/Infinity with None for valid RFC 8259 JSON compliance."""
    if isinstance(obj, float):
        if obj != obj or obj == float("inf") or obj == float("-inf"):
            return None
        return obj
    elif isinstance(obj, dict):
        return {k: _sanitize_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_sanitize_floats(item) for item in obj]
    return obj


def serialize_map_data(data: Union[BaseModel, Dict[str, Any]], indent: Optional[int] = None) -> str:
    """Deterministically serializes MapSpecification or GeoJSON objects to stable JSON string."""
    if isinstance(data, BaseModel):
        raw_dict = data.model_dump()
    else:
        raw_dict = data

    sanitized = _sanitize_floats(raw_dict)
    return json.dumps(sanitized, sort_keys=True, indent=indent, ensure_ascii=False)
