from pathlib import Path
import json

from oie.orchestration.run_context import RunContext
from oie.services.run_analytics_export_service import RunAnalyticsExportService


def test_run_analytics_export_service_writes_json(tmp_path):
    ctx = RunContext.create(
        config={"outputs": {"path": str(tmp_path / "outputs")}},
        flags={},
    )

    service = RunAnalyticsExportService(ctx)
    analytics = {
        "run_id": ctx.run_id,
        "status": "company_pipeline_completed",
        "counts": {
            "jobs": 2,
            "companies": 1,
            "leads": 1,
            "duplicate_jobs": 0,
        },
    }

    out_path = service.export_json(analytics)

    assert out_path.endswith("run_analytics.json")
    assert ctx.paths["run_analytics_json"] == out_path
    assert Path(out_path).exists()

    saved = json.loads(Path(out_path).read_text(encoding="utf-8"))
    assert saved["status"] == "company_pipeline_completed"
    assert saved["counts"]["jobs"] == 2
