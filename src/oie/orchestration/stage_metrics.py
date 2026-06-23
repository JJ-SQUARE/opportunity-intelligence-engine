from __future__ import annotations

from typing import Any, Dict


def build_stage_metrics(checkpoint: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": checkpoint["run_id"],
        "stage": checkpoint["stage"],
        "status": checkpoint["status"],
        "input_count": checkpoint["input_count"],
        "processed_count": checkpoint["processed_count"],
        "output_count": checkpoint["output_count"],
        "rejected_count": checkpoint["rejected_count"],
        "error_count": len(checkpoint["errors"]),
        "provider_usage": checkpoint["provider_usage"],
        "cost_estimate": checkpoint["cost_estimate"],
        "processing_time_seconds": checkpoint["processing_time_seconds"],
    }
