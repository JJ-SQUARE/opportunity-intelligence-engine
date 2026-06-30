from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any

from oie.domain.value_objects import StableId


def to_primitive(value: Any) -> Any:
    if isinstance(value, StableId):
        return str(value)

    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: to_primitive(getattr(value, field.name))
            for field in fields(value)
        }

    if isinstance(value, list):
        return [to_primitive(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key): to_primitive(item)
            for key, item in value.items()
        }

    return value
