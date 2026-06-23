from __future__ import annotations

from typing import Any, Dict


def build_error_record(exc: Exception) -> Dict[str, Any]:
    return {
        "error_type": exc.__class__.__name__,
        "error_message": str(exc),
    }
