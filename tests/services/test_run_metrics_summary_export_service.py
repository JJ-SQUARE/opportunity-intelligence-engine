from pathlib import Path
import json

from oie.orchestration.run_context import RunContext
from oie.services.run_metrics_summary_export_service import RunMetricsSummaryExportService


def test_run_metrics_summary_export_service_writes_json(tmp_path):
    ctx = RunContext.create(
        config={"outputs": {"path": str(tmp_path / "outputs")}},
        flags={},
    )

    service = RunMetricsSummaryExportService(ctx)
    summary = {
        "jobs_collected": 10,
        "companies_detected": 4,
        "provider_errors": {"openai": {"execution_error": 1}},
    }

    out_path = service.export_json(summary)

    assert out_path.endswith("run_metrics_summary.json")
    assert ctx.paths["run_metrics_summary_json"] == out_path
    assert Path(out_path).exists()

    saved = json.loads(Path(out_path).read_text(encoding="utf-8"))
    assert saved["jobs_collected"] == 10
    assert saved["companies_detected"] == 4
    assert saved["provider_errors"]["openai"]["execution_error"] == 1
