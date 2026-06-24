from __future__ import annotations

from typing import TypedDict


class ErrorRecord(TypedDict):
    error_type: str
    error_message: str


def build_error_record(exc: Exception) -> ErrorRecord:
    return {
        "error_type": exc.__class__.__name__,
        "error_message": str(exc),
    }
