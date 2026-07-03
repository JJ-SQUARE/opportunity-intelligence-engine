from __future__ import annotations

from typing import TypedDict


class ErrorRecord(TypedDict):
    error_type: str
    error_message: str


class ProviderNotConfiguredError(RuntimeError):
    """Raised when a required provider client is not configured (missing API key)."""
    pass


def build_error_record(exc: Exception) -> ErrorRecord:
    return {
        "error_type": exc.__class__.__name__,
        "error_message": str(exc),
    }
