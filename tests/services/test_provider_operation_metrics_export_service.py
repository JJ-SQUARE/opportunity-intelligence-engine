from pathlib import Path
import csv
import json

from oie.orchestration.run_context import RunContext
from oie.services.provider_operation_metrics_export_service import ProviderOperationMetricsExportService


def test_provider_operation_metrics_export_service_writes_csv_and_json(tmp_path):
    ctx = RunContext.create(
        config={"outputs": {"path": str(tmp_path / "outputs")}},
        flags={},
    )

    service = ProviderOperationMetricsExportService(ctx)
    rows = [
        {
            "provider": "openai",
            "operation": "classify_company",
            "max_calls": 100,
            "used_calls": 10,
            "remaining_calls": 90,
            "started": 10,
            "success": 9,
            "retry_count": 1,
            "blocked_budget": 0,
            "blocked_provider": 0,
            "errors_timeout": 0,
            "errors_rate_limit": 1,
            "errors_http_5xx": 0,
            "errors_execution_error": 0,
        }
    ]

    csv_path = service.export_csv(rows)
    json_path = service.export_json(rows)

    assert csv_path.endswith("provider_operation_metrics.csv")
    assert json_path.endswith("provider_operation_metrics.json")
    assert ctx.paths["provider_operation_metrics_csv"] == csv_path
    assert ctx.paths["provider_operation_metrics_json"] == json_path

    assert Path(csv_path).exists()
    assert Path(json_path).exists()

    with Path(csv_path).open("r", encoding="utf-8", newline="") as fh:
        saved_rows = list(csv.DictReader(fh))
    assert len(saved_rows) == 1
    assert saved_rows[0]["provider"] == "openai"
    assert saved_rows[0]["operation"] == "classify_company"

    saved_json = json.loads(Path(json_path).read_text(encoding="utf-8"))
    assert len(saved_json) == 1
    assert saved_json[0]["provider"] == "openai"
    assert saved_json[0]["used_calls"] == 10
