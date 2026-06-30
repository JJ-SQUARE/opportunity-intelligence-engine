from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

from oie.domain.value_objects import StableId


def to_primitive(value: Any) -> Any:
    if isinstance(value, StableId):
        return str(value)

    if is_dataclass(value) and not isinstance(value, type):
        return {
            key: to_primitive(item)
            for key, item in asdict(value).items()
        }

    if isinstance(value, list):
        return [to_primitive(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key): to_primitive(item)
            for key, item in value.items()
        }

    return value
