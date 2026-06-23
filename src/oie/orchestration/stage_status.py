from __future__ import annotations

from typing import Any, Dict


def failure_status_for_checkpoint(checkpoint: Dict[str, Any]) -> str:
    return "partial_success" if checkpoint["processed_count"] > 0 else "failed"
